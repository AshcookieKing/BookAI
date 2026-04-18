# BookAI / Bok Studio

Семейный продукт для генерации **историй и книг** с опорой на нейросети: веб-интерфейс (студия фото, видео, книги), Python-модули для текстов и изображений, Telegram-бот и заготовка HTTP API под будущую интеграцию.

## Возможности

| Область | Описание |
|--------|----------|
| **Веб (`web/`)** | React + Vite + TypeScript: загрузка фото, параметры книги (жанр, герой, число страниц, обложка), шаблоны сюжетов, расчёт токенов и тарифов (демо без реальной оплаты). |
| **Маршрутизация** | `HashRouter` — удобно выкладывать статику на shared hosting без настройки nginx под SPA. |
| **`story_engine.py`** | Тексты, vision по изображениям, иллюстрации, TTS через OpenAI-совместимый API. |
| **`privacy_image.py`** | Подготовка изображений перед отправкой в vision (обезличивание). |
| **`gemini_image.py`** | Генерация изображений через Gemini / прокси (APIYI и т.д.). |
| **`bot.py`** | Telegram-бот поверх того же пайплайна. |
| **`backend/main.py`** | Минимальный FastAPI: очереди задач `book` / `image` / `video` (заглушки под продакшен). |

## Структура репозитория

```
.
├── web/                    # Фронтенд Bok Studio
│   ├── src/                # Компоненты, страницы, контекст пользователя (токены)
│   ├── public/             # favicon, .htaccess (Apache, опционально)
│   └── package.json
├── backend/                # FastAPI-заглушки
│   ├── main.py
│   └── requirements.txt
├── story_engine.py         # Движок историй / книг (OpenAI SDK)
├── privacy_image.py
├── gemini_image.py
├── bot.py                  # Telegram
├── requirements.txt        # Python-зависимости корня проекта
├── .env.example            # Шаблон переменных окружения (скопировать в `.env`)
└── README.md
```

В `.gitignore` исключены: `venv/`, `.env`, `web/node_modules/`, `web/dist/`, артефакты Python. Папка **SLServer** и прочие посторонние каталоги не входят в этот репозиторий.

## Требования

- **Node.js** 18+ (для `web/`)
- **Python** 3.10+ (для бота, `story_engine`, FastAPI)

## Веб-интерфейс

```bash
cd web
npm install
npm run dev
```

Откроется dev-сервер Vite (по умолчанию `http://localhost:5173`).

Сборка продакшена:

```bash
cd web
npm run build
```

Готовые файлы — в **`web/dist/`**: заливайте **всё содержимое** `dist` в корень сайта на хостинге (вместе с папкой `assets/`). Для **nginx** может понадобиться правило `try_files` для SPA; при использовании **HashRouter** прямые ссылки вида `/#/studio/book` обычно работают без доп. конфигурации.

Переменная **`base`** в `web/vite.config.ts` задаёт базовый путь для ресурсов (`./` — относительные пути к JS/CSS).

## Python: установка зависимостей

Из корня проекта:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

Для только API-заглушки:

```bash
pip install -r backend/requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните значения. Кратко:

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | Ключ OpenAI или совместимого прокси. |
| `OPENAI_BASE_URL` / `APIYI_BASE_URL` | Необязательно: свой `base_url` для OpenAI SDK. |
| `OPENAI_STORY_MODEL` | Модель текста (по умолчанию `gpt-4o`). |
| `OPENAI_IMAGE_MODEL` | Модель картинок (например `dall-e-3`). |
| `OPENAI_TTS_MODEL` | Озвучка (например `tts-1-hd`). |
| `TELEGRAM_BOT_TOKEN` | Токен бота для `bot.py`. |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Для `gemini_image.py`. |
| `APIYI_GEMINI_HOST` | Хост прокси Gemini при необходимости. |
| `IMAGE_BACKEND`, `NANO_BANANA` | Режимы бэкенда изображений (см. код `story_engine.py` / `gemini_image.py`). |

Секреты **не коммитьте**: держите их только в `.env` локально или в секретах CI.

## Запуск FastAPI (заглушка)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Эндпоинты: `GET /health`, `POST /api/v1/jobs/book`, `.../image`, `.../video`. Подключите сюда реальную генерацию и биллинг.

## Запуск Telegram-бота

После настройки `.env` с `TELEGRAM_BOT_TOKEN`:

```bash
python bot.py
```

(Точка входа и поведение смотрите в `bot.py`.)

## Токены и подписки в UI

В интерфейсе заданы **демонстрационные** цены в условных токенах и планы подписки (`web/src/lib/tokens.ts`, `subscriptions.ts`). Реальное списание и квоты нужно реализовать на сервере и связать с `web/src/lib/api.ts`.

## Участие в разработке

1. Клонировать репозиторий.
2. Ветка от `main`, изменения коммитить осмысленными сообщениями.
3. Перед PR: `npm run build` в `web/`, при необходимости проверка линтера/типов.

## Лицензия

Укажите лицензию по усмотрению автора репозитория.
