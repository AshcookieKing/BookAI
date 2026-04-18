"""
Заглушка HTTP API под Bok Studio.
Подключите сюда вызовы к story_engine / gemini_image и биллинг.

Запуск: uvicorn main:app --reload --port 8080
Прокси из Vite: см. vite.config.ts -> server.proxy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bok Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "service": "bok-studio"}


@app.post("/api/v1/jobs/book")
async def create_book_job(
    title: str = Form(...),
    genre: str = Form(...),
    page_count: int = Form(...),
    token_estimate: int = Form(...),
    photos: list[UploadFile] | None = File(None),
):
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    return {
        "id": job_id,
        "status": "queued",
        "kind": "book",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "token_estimate": token_estimate,
        "title": title,
        "genre": genre,
        "page_count": page_count,
        "photo_count": len(photos or []),
        "message": "Интеграция с генерацией не подключена — заглушка.",
    }


@app.post("/api/v1/jobs/image")
async def create_image_job(
    prompt: str = Form(...),
    token_estimate: int = Form(0),
    photos: list[UploadFile] | None = File(None),
):
    job_id = f"img_{uuid.uuid4().hex[:10]}"
    return {
        "id": job_id,
        "status": "queued",
        "kind": "image",
        "token_estimate": token_estimate,
        "prompt": prompt[:500],
        "photo_count": len(photos or []),
    }


@app.post("/api/v1/jobs/video")
async def create_video_job(
    seconds: int = Form(...),
    script: str = Form(...),
    token_estimate: int = Form(0),
):
    job_id = f"vid_{uuid.uuid4().hex[:10]}"
    return {
        "id": job_id,
        "status": "queued",
        "kind": "video",
        "seconds": seconds,
        "token_estimate": token_estimate,
        "script": script[:800],
    }
