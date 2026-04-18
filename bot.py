"""
Telegram-бот: меню, мастер «книга», «история», «картинка по фото», опциональная озвучка (OpenAI TTS).
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import textwrap
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from story_engine import (
    get_openai_client,
    run_book_pipeline,
    run_image_from_photo,
    run_story_pipeline,
)

_ROOT = Path(__file__).resolve().parent
_ENV_FILE = _ROOT / ".env"
_dotenv_loaded = load_dotenv(_ENV_FILE, override=False)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("storybot")

MAX_PHOTOS = 10


def _kb_book_photos_done() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Все фото загружены", callback_data="book:pd")]])


def _kb_story_photos_done() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Фото готовы", callback_data="story:pd")]])


async def _try_delete_user_command(update: Update) -> None:
    if os.environ.get("BOT_DELETE_USER_COMMANDS", "1").lower() not in ("1", "true", "yes", "on"):
        return
    msg = update.message
    if msg is None:
        return
    try:
        await msg.delete()
    except Exception:
        pass


async def _try_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    if os.environ.get("BOT_DELETE_USER_COMMANDS", "1").lower() not in ("1", "true", "yes", "on"):
        return
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception:
        pass
TELEGRAM_MAX = 4096

# --- Состояния диалогов ---
(
    B_PHOTOS,
    B_GENRE,
    B_ABOUT,
    B_TITLE,
    B_PAGES,
    B_AUDIO,
    B_VOICE,
) = range(10, 17)

(S_PHOTOS, S_HERO, S_ABOUT, S_AUDIO, S_VOICE) = range(20, 25)

(I_PHOTO, I_SCENE, I_STYLE) = range(30, 33)


def main_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📖 Книга"), KeyboardButton("✨ История"), KeyboardButton("🖼 Картинка")],
            [KeyboardButton("📌 Меню"), KeyboardButton("❓ Помощь")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Или выбери кнопку ниже…",
    )


def genre_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🧚 Сказка", callback_data="book:g:Сказка"),
                InlineKeyboardButton("🚀 Приключения", callback_data="book:g:Приключения"),
            ],
            [
                InlineKeyboardButton("💛 Семейная", callback_data="book:g:Семейная"),
                InlineKeyboardButton("🔮 Фэнтези", callback_data="book:g:Фэнтези"),
            ],
            [
                InlineKeyboardButton("😄 Юмор", callback_data="book:g:Юмор"),
                InlineKeyboardButton("🌃 Городское фэнтези", callback_data="book:g:Городское фэнтези"),
            ],
            [InlineKeyboardButton("✏️ Свой жанр (напишу текстом)", callback_data="book:g:__custom__")],
        ]
    )


def voice_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Диктор · onyx", callback_data=f"{prefix}:v:onyx"),
                InlineKeyboardButton("Тёплый · nova", callback_data=f"{prefix}:v:nova"),
            ],
            [
                InlineKeyboardButton("Спокойный · shimmer", callback_data=f"{prefix}:v:shimmer"),
                InlineKeyboardButton("Экспрессивный · fable", callback_data=f"{prefix}:v:fable"),
            ],
            [
                InlineKeyboardButton("Мягкий · alloy", callback_data=f"{prefix}:v:alloy"),
                InlineKeyboardButton("Чёткий · echo", callback_data=f"{prefix}:v:echo"),
            ],
        ]
    )


def style_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Акварель", callback_data="img:s:aq"),
                InlineKeyboardButton("3D Pixar", callback_data="img:s:px"),
            ],
            [
                InlineKeyboardButton("Комикс", callback_data="img:s:cm"),
                InlineKeyboardButton("Реализм", callback_data="img:s:rl"),
            ],
            [InlineKeyboardButton("✏️ Свой стиль текстом", callback_data="img:s:__custom__")],
        ]
    )


def menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📖 Написать книгу", callback_data="flow:book")],
            [InlineKeyboardButton("✨ Написать историю", callback_data="flow:story")],
            [InlineKeyboardButton("🖼 Картинка по фото", callback_data="flow:img")],
            [InlineKeyboardButton("🔄 Обновить подсказки", callback_data="flow:noop")],
        ]
    )


async def download_photo_bytes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bytes:
    photo = update.message.photo[-1]
    f = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await f.download_to_memory(out=buf)
    return buf.getvalue()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = update.effective_chat.id
    await context.bot.send_message(
        cid,
        "Привет! Я помогаю делать **личные книги и истории** из твоих фото — с обложкой и по желанию **озвучкой**.\n\n"
        "Лица на снимках **сначала обезличиваются на твоём устройстве**. Картинки: при наличии **Gemini** — через неё (см. `IMAGE_BACKEND` в `.env`), иначе OpenAI.\n\n"
        "Открой **📌 Меню** или /menu.",
        reply_markup=main_reply_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await _try_delete_user_command(update)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = update.effective_chat.id
    await context.bot.send_message(
        cid,
        "**Как пользоваться**\n\n"
        "• **Книга** — фото → жанр → о ком → название → страницы → озвучка.\n"
        "• **История** — фото → герой → сюжет → озвучка.\n"
        "• **Картинка** — фото → текст → стиль.\n\n"
        "/cancel — выйти из мастера.\n"
        "/menu — меню.\n\n"
        "_Совет:_ опиши, кто на фото — так стабильнее герой на картинке.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    await _try_delete_user_command(update)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = update.effective_chat.id
    # Сначала обновляем нижнюю клавиатуру (нельзя совместить с inline в одном сообщении)
    await context.bot.send_message(cid, "·", reply_markup=main_reply_kb())
    await context.bot.send_message(
        cid,
        "**Главное меню** — выбери действие:",
        reply_markup=menu_inline(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await _try_delete_user_command(update)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_text("Ок, остановились. /menu — снова в меню.", reply_markup=main_reply_kb())
    return ConversationHandler.END


async def menu_end_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выйти из мастера и показать /menu."""
    context.user_data.clear()
    await cmd_menu(update, context)
    return ConversationHandler.END


async def menu_help_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    t = (update.message.text or "").strip()
    if t == "📌 Меню":
        await cmd_menu(update, context)
    elif t == "❓ Помощь":
        await cmd_help(update, context)


async def flow_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q and q.data == "flow:noop":
        await q.answer("Меню ниже 👇")
        await cmd_menu(update, context)


# ----- Книга -----
async def book_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.effective_chat
    if update.callback_query:
        await update.callback_query.answer()
        await _try_delete_message(context, chat.id, update.callback_query.message.message_id)
    context.user_data["book"] = {"photos": []}
    await context.bot.send_message(
        chat.id,
        "**Шаг 1/6 — Фото**\nПришли фото (до 10), затем жми **«Все фото загружены»**.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_kb_book_photos_done(),
    )
    return B_PHOTOS


async def book_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    b = context.user_data.setdefault("book", {})
    pics: list = b.setdefault("photos", [])
    if len(pics) >= MAX_PHOTOS:
        await update.message.reply_text(
            f"Уже {MAX_PHOTOS} фото — это максимум.",
            reply_markup=main_reply_kb(),
        )
        return B_PHOTOS
    pics.append(await download_photo_bytes(update, context))
    await update.message.reply_text(
        f"Сохранено фото **{len(pics)}** / {MAX_PHOTOS}.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return B_PHOTOS


async def book_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    pics = context.user_data.get("book", {}).get("photos", [])
    if not pics:
        await q.edit_message_text(
            "Сначала пришли **хотя бы одно фото**, затем снова нажми кнопку.",
            reply_markup=_kb_book_photos_done(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return B_PHOTOS
    await q.edit_message_text(f"Принято **{len(pics)}** фото. Идём дальше…", parse_mode=ParseMode.MARKDOWN)
    await context.bot.send_message(
        update.effective_chat.id,
        "**Шаг 2/6 — Жанр**\nНажми кнопку или напиши жанр одним сообщением.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=genre_kb(),
    )
    await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
    return B_GENRE


async def book_genre_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    raw = q.data.split(":", 2)[-1]
    if raw == "__custom__":
        await q.edit_message_text(
            "Напиши жанр сообщением или выбери кнопку ниже.",
            reply_markup=genre_kb(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return B_GENRE
    context.user_data.setdefault("book", {})["genre"] = raw[:120]
    await q.edit_message_text(f"Жанр: **{raw}**", parse_mode=ParseMode.MARKDOWN)
    await context.bot.send_message(
        update.effective_chat.id,
        "**Шаг 3/6 — О ком книга?**\nГерои, отношения, конфликт или мечта.",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
    return B_ABOUT


async def book_genre_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = (update.message.text or "").strip()
    nav = ("📖 Книга", "✨ История", "🖼 Картинка", "📌 Меню", "❓ Помощь")
    if not t or t in nav:
        return B_GENRE
    context.user_data.setdefault("book", {})["genre"] = t[:200]
    await update.message.reply_text(
        "**Шаг 3/6 — О ком книга?**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return B_ABOUT


async def book_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault("book", {})["about"] = update.message.text.strip()[:4000]
    await update.message.reply_text(
        "**Шаг 4/6 — Название книги** (можно рабочее, я подправлю в тексте).",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return B_TITLE


async def book_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault("book", {})["title"] = update.message.text.strip()[:200]
    await update.message.reply_text(
        "**Шаг 5/6 — Сколько условных страниц?**\nЧисло от **3** до **60** (это длина глав и объёма текста).",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return B_PAGES


async def book_pages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    digits = re.sub(r"\D", "", update.message.text.strip())
    if not digits:
        await update.message.reply_text(
            "Нужно число, например `12`.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_reply_kb(),
        )
        return B_PAGES
    p = int(digits)
    p = max(3, min(p, 60))
    context.user_data.setdefault("book", {})["pages"] = p
    await update.message.reply_text(
        "**Шаг 6/6 — Озвучка?**\nСгенерировать **MP3** с голосом диктора (разбито на части при длинном тексте).",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Да, с озвучкой 🎙", callback_data="book:a:1"),
                    InlineKeyboardButton("Нет", callback_data="book:a:0"),
                ]
            ]
        ),
    )
    await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
    return B_AUDIO


async def book_audio_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    want = q.data.endswith(":1")
    context.user_data.setdefault("book", {})["wants_audio"] = want
    if want:
        await q.edit_message_text("Выбери **голос** диктора:")
        await context.bot.send_message(
            update.effective_chat.id,
            "Голос озвучки:",
            reply_markup=voice_kb("book"),
        )
        await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
        return B_VOICE
    return await book_finish(update, context)


async def book_voice_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    voice = q.data.rsplit(":", 1)[-1]
    context.user_data.setdefault("book", {})["voice"] = voice
    return await book_finish(update, context)


async def book_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    msg_src = update.effective_message
    b = context.user_data.get("book", {})
    photos: list = b.get("photos", [])
    genre = b.get("genre", "Сказка")
    about = b.get("about", "")
    title = b.get("title", "Без названия")
    pages = int(b.get("pages", 8))
    audio = bool(b.get("wants_audio"))
    voice = (b.get("voice") or "onyx").strip()

    await msg_src.reply_text("⏳ **Пишу книгу**, обложку и при необходимости аудио… Это может занять пару минут.", parse_mode=ParseMode.MARKDOWN)
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    client = get_openai_client()
    loop = asyncio.get_event_loop()

    try:
        text, cover, audios = await loop.run_in_executor(
            None,
            lambda: run_book_pipeline(client, photos, genre, about, title, pages, audio, voice if audio else ""),
        )
    except Exception as e:
        log.exception("book pipeline")
        await msg_src.reply_text(f"Не вышло: {e!s}")
        context.user_data.clear()
        return ConversationHandler.END

    for chunk in textwrap.wrap(text, TELEGRAM_MAX - 80, replace_whitespace=False):
        await context.bot.send_message(chat_id, chunk)
    await context.bot.send_photo(
        chat_id,
        photo=InputFile(io.BytesIO(cover), filename="cover.png"),
        caption="Обложка 📚",
    )
    if audios:
        for i, blob in enumerate(audios):
            await context.bot.send_audio(
                chat_id,
                audio=InputFile(io.BytesIO(blob), filename=f"book_{i+1}.mp3"),
                title=f"Озвучка, часть {i+1}",
                performer="OpenAI TTS",
            )

    context.user_data.clear()
    await context.bot.send_message(chat_id, "Готово! **/menu** — ещё раз.", parse_mode=ParseMode.MARKDOWN, reply_markup=main_reply_kb())
    return ConversationHandler.END


# ----- История -----
async def story_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cid = update.effective_chat.id
    if update.callback_query:
        await update.callback_query.answer()
        await _try_delete_message(context, cid, update.callback_query.message.message_id)
    context.user_data["story"] = {"photos": []}
    await context.bot.send_message(
        cid,
        "**Шаг 1/4 — Фото**\nПришли фото, затем **«Фото готовы»**.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_kb_story_photos_done(),
    )
    return S_PHOTOS


async def story_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    s = context.user_data.setdefault("story", {})
    pics: list = s.setdefault("photos", [])
    if len(pics) >= MAX_PHOTOS:
        await update.message.reply_text("Максимум 10 фото.", reply_markup=main_reply_kb())
        return S_PHOTOS
    pics.append(await download_photo_bytes(update, context))
    await update.message.reply_text(f"Фото {len(pics)}/{MAX_PHOTOS}.", reply_markup=main_reply_kb())
    return S_PHOTOS


async def story_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    pics = context.user_data.get("story", {}).get("photos", [])
    if not pics:
        await q.edit_message_text(
            "Сначала пришли хотя бы одно фото, затем снова нажми кнопку.",
            reply_markup=_kb_story_photos_done(),
        )
        return S_PHOTOS
    await q.edit_message_text("Фото приняты.")
    await context.bot.send_message(
        update.effective_chat.id,
        "**Шаг 2/4 — Имя героя** (условное, для сюжета).",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
    return S_HERO


async def story_hero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault("story", {})["hero"] = update.message.text.strip()[:120]
    await update.message.reply_text(
        "**Шаг 3/4 — О чём история?**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return S_ABOUT


async def story_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault("story", {})["about"] = update.message.text.strip()[:4000]
    await update.message.reply_text(
        "**Шаг 4/4 — Озвучить историю?**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Да 🎙", callback_data="story:a:1"), InlineKeyboardButton("Нет", callback_data="story:a:0")]]
        ),
    )
    await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
    return S_AUDIO


async def story_audio_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    want = q.data.endswith(":1")
    context.user_data.setdefault("story", {})["wants_audio"] = want
    if want:
        await q.edit_message_text("Выбери голос:")
        await context.bot.send_message(update.effective_chat.id, "Голос:", reply_markup=voice_kb("story"))
        await context.bot.send_message(update.effective_chat.id, "·", reply_markup=main_reply_kb())
        return S_VOICE
    return await story_finish(update, context)


async def story_voice_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("story", {})["voice"] = q.data.rsplit(":", 1)[-1]
    return await story_finish(update, context)


async def story_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    s = context.user_data.get("story", {})
    chat_id = update.effective_chat.id
    msg_src = update.effective_message
    photos = s.get("photos", [])
    hero = s.get("hero", "")
    about = s.get("about", "")
    audio = bool(s.get("wants_audio"))
    voice = (s.get("voice") or "nova").strip()

    await msg_src.reply_text("⏳ Пишу историю и обложку…", parse_mode=ParseMode.MARKDOWN)
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    client = get_openai_client()
    loop = asyncio.get_event_loop()
    try:
        text, cover, audios = await loop.run_in_executor(
            None,
            lambda: run_story_pipeline(client, photos, hero, about, audio, voice if audio else ""),
        )
    except Exception as e:
        log.exception("story pipeline")
        await msg_src.reply_text(f"Не вышло: {e!s}")
        context.user_data.clear()
        return ConversationHandler.END
    for chunk in textwrap.wrap(text, TELEGRAM_MAX - 80, replace_whitespace=False):
        await context.bot.send_message(chat_id, chunk)
    await context.bot.send_photo(
        chat_id,
        photo=InputFile(io.BytesIO(cover), filename="story.png"),
        caption="Иллюстрация ✨",
    )
    if audios:
        for i, blob in enumerate(audios):
            await context.bot.send_audio(
                chat_id,
                audio=InputFile(io.BytesIO(blob), filename=f"story_{i+1}.mp3"),
                title=f"Озвучка {i+1}",
                performer="OpenAI TTS",
            )
    context.user_data.clear()
    await context.bot.send_message(chat_id, "Готово! /menu", reply_markup=main_reply_kb())
    return ConversationHandler.END


# ----- Картинка -----
async def img_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cid = update.effective_chat.id
    if update.callback_query:
        await update.callback_query.answer()
        await _try_delete_message(context, cid, update.callback_query.message.message_id)
    context.user_data["img"] = {}
    await context.bot.send_message(
        cid,
        "**Шаг 1/3**\nПришли **одно** фото.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return I_PHOTO


async def img_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        return I_PHOTO
    raw = await download_photo_bytes(update, context)
    context.user_data.setdefault("img", {})["bytes"] = raw
    await update.message.reply_text(
        "**Шаг 2/3**\nКоротко опиши сцену или героя **своими словами** (1–3 предложения). Это помогает сохранить «того же» героя на картинке.\n"
        "Или отправь **пропуск**, написав: `skip`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_reply_kb(),
    )
    return I_SCENE


async def img_scene(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = (update.message.text or "").strip()
    context.user_data.setdefault("img", {})["about"] = "" if t.lower() in ("skip", "пропуск", "-") else t[:2000]
    await update.message.reply_text(
        "**Шаг 3/3 — Стиль**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=style_kb(),
    )
    return I_STYLE


async def img_style_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 2)[-1]
    if key == "__custom__":
        await q.edit_message_text(
            "Напиши стиль сообщением или выбери кнопку ниже.",
            reply_markup=style_kb(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return I_STYLE
    style = STYLE_PRESETS.get(key, STYLE_PRESETS["aq"])
    return await img_run_with_style(update, context, style)


async def img_style_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    st = update.message.text.strip()[:500]
    return await img_run_with_style(update, context, st)


async def img_run_with_style(update: Update, context: ContextTypes.DEFAULT_TYPE, style: str) -> int:
    im = context.user_data.get("img", {})
    raw: Optional[bytes] = im.get("bytes")
    about = im.get("about") or ""
    chat_id = update.effective_chat.id
    msg_src = update.effective_message
    if not raw:
        await msg_src.reply_text("Нет фото. Начни снова: /menu → картинка.")
        context.user_data.clear()
        return ConversationHandler.END
    await msg_src.reply_text("⏳ Рисую картинку…")
    await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
    client = get_openai_client()
    loop = asyncio.get_event_loop()
    try:
        pic = await loop.run_in_executor(None, lambda: run_image_from_photo(client, raw, style, about))
    except Exception as e:
        log.exception("img from photo")
        await msg_src.reply_text(f"Не вышло: {e!s}")
        context.user_data.clear()
        return ConversationHandler.END
    await context.bot.send_photo(
        chat_id,
        photo=InputFile(io.BytesIO(pic), filename="from_photo.png"),
        caption="Готово 🖼",
    )
    context.user_data.clear()
    await context.bot.send_message(chat_id, "/menu — снова в меню", reply_markup=main_reply_kb())
    return ConversationHandler.END



STYLE_PRESETS: dict[str, str] = {
    "aq": "Акварельная детская книга, мягкие краски, бумажная текстура.",
    "px": "Яркий 3D мультфильм, добрый свет, насыщенные цвета.",
    "cm": "Современный комикс, чистые контуры, динамика.",
    "rl": "Реалистичная цифровая иллюстрация, киношный свет, тепло.",
}


def main() -> None:
    import os

    if not _ENV_FILE.is_file():
        log.warning(".env не найден: %s", _ENV_FILE)
    elif not _dotenv_loaded:
        log.warning(".env не прочитан")

    book_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(book_entry, pattern=r"^flow:book$"),
            MessageHandler(filters.Regex(r"^📖 Книга$"), book_entry),
        ],
        states={
            B_PHOTOS: [
                MessageHandler(filters.PHOTO, book_add_photo),
                CallbackQueryHandler(book_photos_done, pattern=r"^book:pd$"),
            ],
            B_GENRE: [
                CallbackQueryHandler(book_genre_cb, pattern=r"^book:g:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_genre_text),
            ],
            B_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_about)],
            B_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_title)],
            B_PAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_pages)],
            B_AUDIO: [CallbackQueryHandler(book_audio_cb, pattern=r"^book:a:")],
            B_VOICE: [CallbackQueryHandler(book_voice_cb, pattern=r"^book:v:")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu_end_conversation),
        ],
        name="book",
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    story_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(story_entry, pattern=r"^flow:story$"),
            MessageHandler(filters.Regex(r"^✨ История$"), story_entry),
        ],
        states={
            S_PHOTOS: [
                MessageHandler(filters.PHOTO, story_add_photo),
                CallbackQueryHandler(story_photos_done, pattern=r"^story:pd$"),
            ],
            S_HERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, story_hero)],
            S_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, story_about)],
            S_AUDIO: [CallbackQueryHandler(story_audio_cb, pattern=r"^story:a:")],
            S_VOICE: [CallbackQueryHandler(story_voice_cb, pattern=r"^story:v:")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("menu", menu_end_conversation)],
        name="story",
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    img_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(img_entry, pattern=r"^flow:img$"),
            MessageHandler(filters.Regex(r"^🖼 Картинка$"), img_entry),
        ],
        states={
            I_PHOTO: [MessageHandler(filters.PHOTO, img_photo)],
            I_SCENE: [MessageHandler(filters.TEXT & ~filters.COMMAND, img_scene)],
            I_STYLE: [
                CallbackQueryHandler(img_style_cb, pattern=r"^img:s:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, img_style_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("menu", menu_end_conversation)],
        name="img",
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(f"Нет TELEGRAM_BOT_TOKEN. Создай {_ENV_FILE}")

    app = Application.builder().token(token).post_init(post_init_commands).build()
    app.add_handler(book_conv)
    app.add_handler(story_conv)
    app.add_handler(img_conv)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CallbackQueryHandler(flow_noop, pattern=r"^flow:noop$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r"^(📌 Меню|❓ Помощь)$"), menu_help_reply)
    )

    log.info("Бот запущен…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def post_init_commands(app: Application) -> None:
    cmds = [
        BotCommand("menu", "Главное меню"),
        BotCommand("help", "Помощь"),
        BotCommand("cancel", "Отменить мастер"),
        BotCommand("start", "Приветствие"),
    ]
    await app.bot.set_my_commands(cmds)


if __name__ == "__main__":
    main()
