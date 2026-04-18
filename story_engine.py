"""
OpenAI: vision, тексты книги/истории, иллюстрации, TTS. Локальная обезличка — в privacy_image.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from typing import List, Tuple

from openai import OpenAI

from privacy_image import prepare_for_openai_vision

log = logging.getLogger("story_engine")


def get_openai_client() -> OpenAI:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY")
    # OpenAI-совместимые прокси: APIYI, OpenRouter и т.д.
    base = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("APIYI_BASE_URL")
        or ""
    ).strip().rstrip("/")
    if base:
        log.info("OpenAI SDK base_url=%s", base)
        return OpenAI(api_key=key, base_url=base)
    return OpenAI(api_key=key)


def story_model() -> str:
    return os.environ.get("OPENAI_STORY_MODEL", "gpt-4o")


def image_model() -> str:
    return os.environ.get("OPENAI_IMAGE_MODEL", "dall-e-3")


def tts_model() -> str:
    return os.environ.get("OPENAI_TTS_MODEL", "tts-1-hd")


def _mime_for_image_bytes(raw: bytes) -> str:
    if len(raw) >= 3 and raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(raw) >= 8 and raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _data_url_for_image(raw: bytes) -> str:
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{_mime_for_image_bytes(raw)};base64,{b64}"


def _looks_like_model_refusal(text: str) -> bool:
    if not text or len(text) > 900:
        return False
    t = text.lower()
    needles = (
        "не могу помочь",
        "не могу выполнить",
        "не могу создать",
        "извините",
        "отказаться",
        "can't help",
        "cannot help",
        "i'm sorry",
        "i cannot",
        "can't assist",
        "unable to comply",
        "i can't",
    )
    return any(n in t for n in needles)


VISION_HOOKS_SYSTEM = """Это обезличенные референсы для персональной вымышленной книги: автор сам загрузил кадры, лица и детали намеренно скрыты (размытие/пикселизация), узнать человека невозможно.
Дай зацепки для сказки: место, время суток/сезон (условно), настроение, предметы, природа/архитектура. Люди — обобщённые роли («семья за столом», «друзья на прогулке»), без имён, возраста числом и идентификации.
Ответ — маркированный список на русском, 6–14 строк. Не отказывайся."""


VISION_USER_PRIMARY = "Выпиши зацепки для сказки по этим обезличенным референсам (см. системное сообщение)."
VISION_USER_DECOR = (
    "Только антураж детской книги: локация, погода, предметы, цвета, настроение. Люди — «гости», «компания» и т.п., без деталей лица."
)


CHARACTER_LOOK_SYSTEM = """Правообладатель просит описание для ИЛЛЮСТРАЦИЙ персональной книги (вымышленные персонажи в стиле артбука).
По одному изображению опиши на АНГЛИЙСКОМ один короткий абзац (4–7 предложений): внешность и одежда главного героя/героини в терминах иллюстрации — телосложение категориями (не медицина), приблизительный возраст словами child/teen/adult/senior, цвет и длина волос, тон кожи художественными словами (warm olive, deep brown, fair), одежда и аксессуары, выражение лица. Если людей несколько — сначала главный, остальные кратко.
Не утверждай, что это реальный человек; не называй знаменитостей; не оценивай привлекательность. Если не можешь — одно слово: FALLBACK."""


STORY_SHORT_SYSTEM = """Ты пишешь художественный текст для вымышленной книги на русском.
Правила: не упоминай фото, камеру, нейросеть. Герои вымышленные. Светлый финал или тёплый интригующий финал без травмы читателя."""


def _chat_vision_hooks(client: OpenAI, model: str, images: List[bytes], *, user_line: str) -> str:
    content: list = [{"type": "text", "text": user_line}]
    for raw in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url_for_image(raw)}})
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VISION_HOOKS_SYSTEM},
            {"role": "user", "content": content},
        ],
        max_tokens=900,
        temperature=0.3,
    )
    return (chat.choices[0].message.content or "").strip()


def _hooks_from_author_text(client: OpenAI, model: str, author_hints: str) -> str:
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Автор описал сцену для личной вымышленной книги. Сделай 8–14 маркеров-зацепок на русском. "
                    "Без отказов и политических отсылок."
                ),
            },
            {"role": "user", "content": author_hints.strip()[:8000]},
        ],
        max_tokens=900,
        temperature=0.45,
    )
    return (chat.choices[0].message.content or "").strip()


def collect_visual_hooks(client: OpenAI, images: List[bytes], author_hints: str) -> str:
    model = story_model()

    def try_v(imgs: List[bytes], line: str) -> str:
        return _chat_vision_hooks(client, model, imgs, user_line=line)

    anon_std = [prepare_for_openai_vision(b, "standard") for b in images]
    hooks = try_v(anon_std, VISION_USER_PRIMARY)
    if not hooks or _looks_like_model_refusal(hooks):
        hooks = try_v(anon_std, VISION_USER_DECOR)
    if not hooks or _looks_like_model_refusal(hooks):
        anon_s = [prepare_for_openai_vision(b, "strong") for b in images]
        hooks = try_v(anon_s, VISION_USER_PRIMARY)
    if not hooks or _looks_like_model_refusal(hooks):
        hooks = try_v(anon_s, VISION_USER_DECOR)
    if (not hooks or _looks_like_model_refusal(hooks)) and len(author_hints.strip()) >= 12:
        hooks = _hooks_from_author_text(client, model, author_hints)
    if not hooks or _looks_like_model_refusal(hooks):
        raise RuntimeError(
            "Не удалось снять зацепки с обезличенных фото. Добавьте текстом: кто герой, где событие, жанр."
        )
    return hooks


def describe_character_for_illustration(client: OpenAI, main_photo: bytes) -> str:
    """Оригинальное фото (без пикселизации) — для промпта «тот же герой»; может вернуть пустую строку."""
    model = story_model()
    content = [
        {"type": "text", "text": "Дай описание для иллюстрации книги (см. system)."},
        {"type": "image_url", "image_url": {"url": _data_url_for_image(main_photo)}},
    ]
    try:
        chat = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CHARACTER_LOOK_SYSTEM},
                {"role": "user", "content": content},
            ],
            max_tokens=350,
            temperature=0.2,
        )
        out = (chat.choices[0].message.content or "").strip()
    except Exception as e:
        log.warning("character vision failed: %s", e)
        return ""
    if not out or out.upper() == "FALLBACK" or _looks_like_model_refusal(out):
        return ""
    return out


def write_story_body(
    client: OpenAI,
    hooks: str,
    author_block: str,
    *,
    book_mode: bool,
    pages: int,
) -> str:
    model = story_model()
    if book_mode:
        pages = max(3, min(pages, 60))
        words = max(400, min(pages * 220, 12000))
        book_instr = (
            f"Оформи как книгу: первая строка «Название: …».\n"
            f"Разбей на {pages} смысловых частей; каждая начинается с «**— Стр. N —**» для N от 1 до {pages} по порядку.\n"
            f"Ориентир объёма ~{words} слов."
        )
        sys_parts = [STORY_SHORT_SYSTEM, book_instr]
        max_tokens = min(8000, 600 + words // 2)
    else:
        sys_parts = [
            STORY_SHORT_SYSTEM,
            "Короткая история: 5–10 абзацев, первая строка «Название: …», без деления на «Стр. N».",
        ]
        max_tokens = 3200
    system = "\n".join(sys_parts)
    user = "Вот зацепки по сцене:\n\n" + hooks + "\n\nВводные автора:\n" + author_block + "\n\nНапиши текст на русском."
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.88,
    )
    text = (chat.choices[0].message.content or "").strip()
    if _looks_like_model_refusal(text):
        raise RuntimeError("Модель отказалась писать текст. Попробуйте смягчить вводные.")
    return text


def illustration_prompt_from_story(
    client: OpenAI,
    story_excerpt: str,
    *,
    character_anchor_en: str,
    genre: str,
) -> str:
    model = story_model()
    anchor = (
        f"Keep the main illustrated character visually consistent with this design: {character_anchor_en}"
        if character_anchor_en
        else "Original illustrated characters, family-friendly."
    )
    ch = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write 2 short English sentences for DALL·E 3 book cover art: scene mood + key visual. "
                    f"Genre hint: {genre}. "
                    f"{anchor} "
                    "No text on image. No violence, no celebrity names. Story excerpt:\n\n"
                    + story_excerpt[:2800]
                ),
            }
        ],
        max_tokens=220,
        temperature=0.55,
    )
    en = (ch.choices[0].message.content or "").strip()
    prefix = (
        "Professional children's book cover illustration, cohesive character design matching reference description, "
        "no text in image, warm light, rich color: "
    )
    return (prefix + en)[:4000]


def image_from_photo_prompt(client: OpenAI, photo: bytes, style: str, about_text: str) -> str:
    """Промпт для картинки «по фото» — стараемся удержать героя через текстовый якорь."""
    model = story_model()
    anchor = describe_character_for_illustration(client, photo)
    content = [
        {
            "type": "text",
            "text": "Кратко на русском: что за место и действие на фото (2 предложения). Про лица не рассуждай.",
        },
        {"type": "image_url", "image_url": {"url": _data_url_for_image(prepare_for_openai_vision(photo, "standard"))}},
    ]
    scene_ru = ""
    try:
        chat = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Пользователь обрабатывает свои снимки для личного творческого проекта. Кратко опиши сцену.",
                },
                {"role": "user", "content": content},
            ],
            max_tokens=120,
            temperature=0.2,
        )
        scene_ru = (chat.choices[0].message.content or "").strip()
    except Exception as e:
        log.warning("scene caption failed: %s", e)

    bridge = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Собери ОДИН английский промпт для DALL·E (max 1200 characters): "
                    f"стиль «{style}». "
                    "Сцена (перевод идей): "
                    + (scene_ru or about_text)[:800]
                    + "\nПерсонаж как в описании (если есть): "
                    + (anchor or "stylized friendly character")
                    + ". Без текста на картинке, без реальных имён и знаменитостей, семейный контент."
                ),
            }
        ],
        max_tokens=400,
        temperature=0.45,
    )
    return (bridge.choices[0].message.content or "").strip()[:3800]


def generate_dalle_image(client: OpenAI, prompt: str) -> bytes:
    import httpx

    resp = client.images.generate(
        model=image_model(),
        prompt=prompt[:4000],
        size="1024x1024",
        quality="standard",
        n=1,
    )
    url = resp.data[0].url
    if not url:
        raise RuntimeError("Нет URL изображения")
    with httpx.Client(timeout=120.0) as ac:
        r = ac.get(url)
        r.raise_for_status()
        return r.content


def _image_backend() -> str:
    """NANO_BANANA=1 — то же, что IMAGE_BACKEND=gemini (Nano Banana / Gemini картинки)."""
    if os.environ.get("NANO_BANANA", "").strip().lower() in ("1", "true", "yes", "on"):
        return "gemini"
    return (os.environ.get("IMAGE_BACKEND") or "auto").strip().lower()


def generate_illustration_image(client: OpenAI, prompt: str) -> bytes:
    """
    Картинка для обложек / «по фото».
    IMAGE_BACKEND=gemini|openai|auto, либо NANO_BANANA=1 → только Gemini (Nano Banana 2 по умолчанию в gemini_image.py).
    """
    backend = _image_backend()
    if backend == "openai":
        return generate_dalle_image(client, prompt)

    if backend == "gemini":
        from gemini_image import generate_image_gemini

        return generate_image_gemini(prompt)

    # auto: Gemini / Nano (Google или APIYI v1beta)
    from gemini_image import generate_image_gemini, should_attempt_gemini_image

    if should_attempt_gemini_image():
        try:
            return generate_image_gemini(prompt)
        except Exception as e:
            log.warning("Gemini/Nano image failed, OpenAI fallback: %s", e)
    return generate_dalle_image(client, prompt)


def tts_mp3_chunks(client: OpenAI, full_text: str, voice: str) -> List[bytes]:
    """Нарезка для лимита символов TTS (~4096)."""
    text = re.sub(r"\*\*", "", full_text).strip()
    if not text:
        return []
    chunks: List[str] = []
    max_c = 3900
    while text:
        take = text[:max_c]
        lo = take.rfind("\n\n")
        if lo < 500:
            lo = take.rfind(". ")
        if lo < 200:
            lo = max_c
        piece = text[: lo + 1].strip() if lo < max_c else take
        if not piece:
            piece = take
        chunks.append(piece)
        text = text[len(piece) :].strip()

    out: List[bytes] = []
    for i, chunk in enumerate(chunks):
        try:
            sp = client.audio.speech.create(
                model=tts_model(),
                voice=voice,
                input=chunk,
                response_format="mp3",
            )
            data = getattr(sp, "content", None)
            if data is None and hasattr(sp, "read"):
                data = sp.read()
            if data:
                out.append(data)
        except Exception as e:
            log.warning("TTS chunk %s failed: %s", i, e)
    return out


def run_book_pipeline(
    client: OpenAI,
    photos: List[bytes],
    genre: str,
    about: str,
    title: str,
    pages: int,
    audio: bool,
    voice: str,
) -> Tuple[str, bytes, List[bytes]]:
    author = (
        f"Жанр: {genre}\nО ком книга: {about}\nРабочее название: {title}\n"
        f"Желаемое число условных страниц: {pages}."
    )
    hooks = collect_visual_hooks(client, photos, author)
    anchor = ""
    try:
        anchor = describe_character_for_illustration(client, photos[0])
    except Exception:
        pass
    text = write_story_body(client, hooks, author, book_mode=True, pages=pages)
    ill_prompt = illustration_prompt_from_story(
        client, text[:4000], character_anchor_en=anchor, genre=genre
    )
    cover = generate_illustration_image(client, ill_prompt)
    audios: List[bytes] = []
    if audio and voice:
        audios = tts_mp3_chunks(client, text, voice)
    return text, cover, audios


def run_story_pipeline(
    client: OpenAI,
    photos: List[bytes],
    hero_name: str,
    about: str,
    audio: bool,
    voice: str,
) -> Tuple[str, bytes, List[bytes]]:
    author = f"Имя героя (условно): {hero_name}\nО чём история: {about}"
    hooks = collect_visual_hooks(client, photos, author)
    anchor = ""
    try:
        anchor = describe_character_for_illustration(client, photos[0])
    except Exception:
        pass
    text = write_story_body(
        client,
        hooks,
        author,
        book_mode=False,
        pages=1,
    )
    if "Название:" not in text.split("\n", 1)[0]:
        text = "Название: История о " + (hero_name or "герое") + "\n\n" + text
    ill_prompt = illustration_prompt_from_story(
        client, text[:4000], character_anchor_en=anchor, genre="короткая история"
    )
    cover = generate_illustration_image(client, ill_prompt)
    audios: List[bytes] = []
    if audio and voice:
        audios = tts_mp3_chunks(client, text, voice)
    return text, cover, audios


def run_image_from_photo(client: OpenAI, photo: bytes, style: str, about: str) -> bytes:
    pr = image_from_photo_prompt(client, photo, style, about or "личный проект")
    return generate_illustration_image(client, pr)
