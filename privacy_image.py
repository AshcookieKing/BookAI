"""
Локальная подготовка снимков перед OpenAI Vision: лица неузнаваемы, сцена сохраняется.
Нужен Pillow и/или OpenCV (достаточно одного; лучше оба).
"""

from __future__ import annotations

import io
import logging
import sys
from typing import List

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageFilter

    _HAS_PIL = True
except ImportError:
    Image = None  # type: ignore
    ImageFilter = None  # type: ignore
    _HAS_PIL = False

try:
    import cv2
    import numpy as np

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    _HAS_CV2 = False


def _die_missing_deps() -> None:
    exe = sys.executable or "python"
    print(
        "Не установлены Pillow (модуль PIL) и OpenCV — нужен хотя бы один пакет.\n"
        f'Выполните тем же Python, которым запускаете бота:\n'
        f'  "{exe}" -m pip install Pillow opencv-python-headless\n'
        f"или:\n"
        f'  "{exe}" -m pip install -r requirements.txt',
        file=sys.stderr,
    )
    raise SystemExit(1)


def _pixelate_pil(pil_im: "Image.Image", factor: int) -> "Image.Image":
    w0, h0 = pil_im.size
    sw = max(1, w0 // factor)
    sh = max(1, h0 // factor)
    small = pil_im.resize((sw, sh), Image.Resampling.LANCZOS)
    return small.resize((w0, h0), Image.Resampling.NEAREST)


def _blur_face_regions_bgr(img_bgr, mode: str) -> None:
    if not _HAS_CV2 or img_bgr is None or img_bgr.size == 0:
        return
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    kernel = 77 if mode == "standard" else 111
    kernel = kernel | 1
    cascades: List[str] = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_profileface.xml",
    ]
    for name in cascades:
        path = cv2.data.haarcascades + name
        cascade = cv2.CascadeClassifier(path)
        if cascade.empty():
            continue
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.06,
            minNeighbors=3,
            minSize=(28, 28),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        for (x, y, fw, fh) in faces:
            pad_x = int(0.4 * fw)
            pad_y = int(0.5 * fh)
            x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
            x2 = min(img_bgr.shape[1], x + fw + pad_x)
            y2 = min(img_bgr.shape[0], y + fh + pad_y)
            roi = img_bgr[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            roi = cv2.GaussianBlur(roi, (kernel, kernel), 0)
            img_bgr[y1:y2, x1:x2] = roi


def _prepare_with_pil(raw: bytes, mode: str) -> bytes:
    assert Image is not None and ImageFilter is not None
    im = Image.open(io.BytesIO(raw)).convert("RGB")

    if _HAS_CV2:
        img_bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        _blur_face_regions_bgr(img_bgr, mode)
        im = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    else:
        log.warning(
            "opencv не установлен — только пикселизация. "
            'Установите: python -m pip install opencv-python-headless'
        )

    factor = (16 if mode == "standard" else 8) if _HAS_CV2 else (10 if mode == "standard" else 6)
    im = _pixelate_pil(im, factor)
    blur_r = 1.1 if mode == "standard" else 2.2
    if not _HAS_CV2:
        blur_r += 0.9
    im = im.filter(ImageFilter.GaussianBlur(radius=blur_r))

    out = io.BytesIO()
    im.save(out, format="JPEG", quality=86, optimize=True)
    return out.getvalue()


def _prepare_cv2_only(raw: bytes, mode: str) -> bytes:
    if not _HAS_CV2:
        _die_missing_deps()
    buf = np.frombuffer(raw, dtype=np.uint8)
    img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Не удалось прочитать изображение (cv2.imdecode).")

    _blur_face_regions_bgr(img_bgr, mode)

    h, w = img_bgr.shape[:2]
    factor = 16 if mode == "standard" else 8
    nw = max(1, w // factor)
    nh = max(1, h // factor)
    small = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    img_bgr = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    blur_k = 5 if mode == "standard" else 9
    k = blur_k | 1
    img_bgr = cv2.GaussianBlur(img_bgr, (k, k), 0)

    ok, enc = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
    if not ok:
        raise RuntimeError("cv2.imencode не смог сохранить JPEG.")
    return enc.tobytes()


def prepare_for_openai_vision(raw: bytes, mode: str = "standard") -> bytes:
    """
    mode:
      standard — размытие лиц (если есть OpenCV) + пикселизация;
      strong   — сильнее пикселизация и размытие.
    """
    if _HAS_PIL:
        return _prepare_with_pil(raw, mode)
    if _HAS_CV2:
        log.warning(
            "Pillow не установлен — используется только OpenCV (pip install Pillow для лучшего качества)."
        )
        return _prepare_cv2_only(raw, mode)
    _die_missing_deps()
