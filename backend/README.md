# MAX Publisher AI backend v0.6.1

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

## RSS reader (v0.5.1)

The backend exposes two read-only endpoints:

- `GET /api/rss/feeds` — lists the built-in public feed directory.
- `GET /api/rss/items?query=<text>&source=<feed_id>&limit=40` — fetches and parses selected feeds.

The allowlist includes iXBT news/articles, 3DNews hardware/software/phones and Overclockers.ru news/reviews. Feed URLs are fixed in `main.py`; arbitrary URLs are not accepted. RSS downloads are streamed with a 2 MB cap, requests do not follow redirects, and feed requests are fetched concurrently with bounded connection limits. RSS entries contain title, summary, source, publication date and original article URL. They are editorial content only and must not be treated as price/discount data. Check publisher terms before republishing excerpts.


## Groq Cloud integration (v0.6.0)

Groq is the default OpenAI-compatible cloud provider. The backend defaults are:

- `CLOUD_AI_PROVIDER=groq`
- `CLOUD_AI_BASE_URL=https://api.groq.com/openai/v1`
- `CLOUD_AI_MODEL=openai/gpt-oss-20b`
- `CLOUD_AI_API_KEY` — secret configured only in the backend host's environment settings.

The key is never returned by `/api/config`, placed in frontend code, or sent to the browser. The frontend's `APP_API_KEY` is a separate application credential and is not the Groq key.

### Age and account ownership

Groq's current Services Agreement requires the Groq Cloud account holder to be at least 18. A parent/legal guardian or other adult project owner must create and manage the provider account, accept the agreement, control the key, and review service and privacy settings. The adult owner is responsible for ensuring any app use by minors complies with applicable rules. A minor must not create the Groq account, accept the provider agreement, or handle the provider secret. Never share the Groq key in chat, GitHub issues, commits or frontend settings.

### Free-tier controls

Groq publishes model-specific organization-level RPM, RPD, TPM and TPD limits. Exact current values are shown in the adult account's Groq Console Limits page and may change. The selected model is configurable by environment variable. HTTP 429 responses must be treated as quota limits; the app must not retry continuously.

### Data handling

Send only the information needed to draft a post. Do not send credentials, private customer data or unrelated personal information. The adult owner should review Groq's current data-retention terms before using the service with sensitive material.


## RSS-aware AI editor (v0.6.1)

The authenticated `POST /api/ai/draft` endpoint accepts `content_type=product|rss`. RSS mode receives title, summary, source, publication date and original URL, then asks the model for a concise paraphrase without invented facts or long copied excerpts. The source attribution and original link are included in the prompt. Product mode retains the existing price/discount safeguards.

The frontend adds a distinct “Переписать с AI” action and style selector. It requires a configured backend URL and session-only `APP_API_KEY`. If not configured, the UI explains that AI is unavailable rather than silently presenting a local template as AI output. Provider quota HTTP 429 is surfaced as a quota message; no automatic retry loop is performed.
