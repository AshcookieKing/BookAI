"""
Картинки через Google Gemini или через **API易 (APIYI)**.

**Nano Banana 2**: `gemini-3.1-flash-image-preview`.

- Официальный Google: `google-genai` + `GEMINI_API_KEY`.
- **APIYI**: тот же токен, что и для чата (`OPENAI_API_KEY`), endpoint `v1beta/...:generateContent`
  (см. docs.apiyi.com — Nano Banana 2). Включите `GEMINI_IMAGE_VIA_APIYI=1`.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Any, List

import httpx

log = logging.getLogger(__name__)


def gemini_image_model() -> str:
    # По умолчанию Nano Banana 2 (см. Google AI docs: gemini-3.1-flash-image-preview)
    return os.environ.get(
        "GEMINI_IMAGE_MODEL",
        "gemini-3.1-flash-image-preview",
    ).strip()


def _use_apiyi_nano() -> bool:
    for name in ("GEMINI_IMAGE_VIA_APIYI", "NANO_BANANA_APIYI"):
        if os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _apiyi_bearer_key() -> str:
    return (os.environ.get("OPENAI_API_KEY") or os.environ.get("APIYI_API_KEY") or "").strip()


def apiyi_gemini_host() -> str:
    """Хост без /v1 — для путей v1beta."""
    return (os.environ.get("APIYI_GEMINI_HOST") or "https://api.apiyi.com").strip().rstrip("/")


def should_attempt_gemini_image() -> bool:
    """Есть Google-ключ или включена отдача Nano через APIYI с токеном."""
    g = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if g:
        return True
    if _use_apiyi_nano() and _apiyi_bearer_key():
        return True
    return False


def generate_nano_banana_via_apiyi(prompt: str) -> bytes:
    """
    Nano Banana / Nano Banana 2 через API易 (не OpenAI images API).
    Документация: POST .../v1beta/models/{model}:generateContent
    """
    key = _apiyi_bearer_key()
    if not key:
        raise RuntimeError("Для APIYI Nano нужен OPENAI_API_KEY (или APIYI_API_KEY)")

    model = gemini_image_model()
    host = apiyi_gemini_host()
    url = f"{host}/v1beta/models/{model}:generateContent"

    text = (prompt or "").strip()[:8000]
    if not text:
        raise ValueError("Пустой промпт для картинки")

    aspect = os.environ.get("NANO_IMAGE_ASPECT_RATIO", "1:1").strip()
    size = os.environ.get("NANO_IMAGE_SIZE", "1K").strip()

    body: dict = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect, "imageSize": size},
        },
    }

    log.info("APIYI Nano Banana: model=%s url=%s", model, url)
    with httpx.Client(timeout=180.0) as client:
        r = client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"APIYI image HTTP {r.status_code}: {r.text[:500]}")
        data = r.json()

    cands = data.get("candidates") or []
    if not cands:
        raise RuntimeError(f"APIYI: нет candidates в ответе: {str(data)[:400]}")

    parts = (cands[0].get("content") or {}).get("parts") or []
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if isinstance(inline, dict) and inline.get("data"):
            raw = inline["data"]
            return base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)

    raise RuntimeError("APIYI: в ответе нет inlineData с изображением")


def _extract_parts(response: Any) -> List[Any]:
    if hasattr(response, "parts") and response.parts:
        return list(response.parts)
    cands = getattr(response, "candidates", None) or []
    if not cands:
        return []
    c0 = cands[0]
    content = getattr(c0, "content", None)
    parts = getattr(content, "parts", None) if content else None
    return list(parts) if parts else []


def generate_image_gemini(prompt: str) -> bytes:
    """Текст → PNG bytes (Google SDK или APIYI v1beta)."""
    if _use_apiyi_nano():
        return generate_nano_banana_via_apiyi(prompt)

    from google import genai

    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "Задайте GEMINI_API_KEY (Google) или GEMINI_IMAGE_VIA_APIYI=1 + OPENAI_API_KEY (APIYI)"
        )

    client = genai.Client(api_key=key)
    text = (prompt or "").strip()[:8000]
    if not text:
        raise ValueError("Пустой промпт для картинки")

    model_id = gemini_image_model()
    log.info("Gemini image: model=%s", model_id)
    response = client.models.generate_content(
        model=model_id,
        contents=[text],
    )

    parts = _extract_parts(response)
    if not parts:
        log.warning("Gemini: нет parts, ответ: %s", response)

    for part in parts:
        if getattr(part, "text", None):
            continue
        if hasattr(part, "as_image"):
            try:
                img = part.as_image()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b = buf.getvalue()
                if b:
                    return b
            except Exception as e:
                log.debug("part.as_image(): %s", e)

        inline = getattr(part, "inline_data", None)
        if inline is not None:
            raw = getattr(inline, "data", None)
            if raw is not None:
                return raw if isinstance(raw, bytes) else bytes(raw)

    raise RuntimeError(
        "Gemini не вернул изображение. Проверьте модель в GEMINI_IMAGE_MODEL и квоту API."
    )
