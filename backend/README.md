# MAX Publisher AI backend v0.3

FastAPI service for authorized product-feed ingestion, hybrid AI drafts and explicitly confirmed MAX channel publishing.

## Run locally

```bash
python -m venv .venv
# activate the environment, then:
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Copy `.env.example` to `.env` and load it using your host's environment-variable settings. Do not commit the real `.env` file.

## Endpoints

- `GET /api/health` — health and version.
- `GET /api/config` — integration readiness (never returns secrets).
- `POST /api/search` — queries configured HTTPS JSON feeds.
- `POST /api/ai/draft` — hybrid Ollama-first, cloud-fallback text draft; requires `X-API-Key`.
- `POST /api/max/publish` — sends a post to the configured MAX channel; requires `X-API-Key` and `confirmed: true`.

Interactive OpenAPI docs: `/api/docs`.

## Feed adapter contract

Each configured source URL must be HTTPS and return either a JSON array or an object with an `items` array. Each item may contain `id`, `name` or `title`, `price`, `old_price`, `url`, `image`, `category`, `currency`, `checked_at`.

This is an ingestion contract, not a claim that a store exposes a public buyer API. Configure only feeds/APIs that the account is authorized to use. Yandex Market seller Partner API is not the same as a general buyer catalog search API. Ozon, DNS, M.Video and Citilink feeds require a suitable official, affiliate or licensed provider. Until a feed is configured, that source remains unavailable and returns no products.

## AI providers

Both providers use an OpenAI-compatible `/chat/completions` endpoint. For Ollama, configure a backend-reachable base URL and model. For cloud, configure base URL, model and key. The cloud key is never sent to the browser. In hybrid mode Ollama is attempted first, then cloud.

## MAX publishing

The service uses `POST https://platform-api2.max.ru/messages?chat_id=...` with `Authorization: <bot token>`. The bot must be added to the destination channel with permission to publish. Keep the token only in backend environment variables. Every request requires explicit `confirmed: true`; the service does not auto-publish.

## Deployment

Build the container using this Dockerfile on a backend host that supports environment variables and HTTPS. Set `CORS_ORIGINS` to the exact GitHub Pages origin and configure a long random `APP_API_KEY`. Do not expose the backend without authentication for privileged endpoints.

GitHub Pages remains the static frontend host; it cannot run FastAPI, Ollama or keep secrets.
