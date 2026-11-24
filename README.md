# MAX Publisher AI Web — v0.3

Mobile-first PWA and a separate FastAPI backend for preparing digital-technology deal posts for a MAX channel.

## Frontend v0.3

- Mobile dashboard, search filters, product editor and local draft queue.
- Backend settings panel: HTTPS API URL and session-only APP_API_KEY.
- Search uses the configured backend when its URL is set; demo catalog is used only when no backend URL is configured.
- AI draft generation uses the backend when a URL and APP_API_KEY are supplied.
- A draft can be explicitly sent to MAX after a confirmation prompt; successful delivery requires a configured backend and MAX bot credentials.
- PWA cache is versioned and updated for v0.3.

## Backend

See [backend/README.md](backend/README.md). The FastAPI service provides health/config, authorized JSON-feed ingestion, hybrid Ollama/cloud-compatible AI drafting and confirmed MAX Bot API publishing.

Deploy the backend as a separate HTTPS container service. A Render Blueprint is included in `render.yaml` for a free test deployment. Free Render services sleep after 15 minutes of inactivity and can take about a minute to wake; their local filesystem is ephemeral. GitHub Pages hosts only the static frontend and cannot run Python or store integration secrets.

## Sources and accuracy

The backend does not scrape store websites. It accepts HTTPS JSON feeds that the owner is authorized to use. Configure the source feed URLs in backend environment variables. A store showing as not configured returns no live products.

The v0.2 demo catalog is illustrative only. Do not treat its products, prices or discount percentages as current offers.

## Required configuration before live use

- Backend host with HTTPS and environment-variable support.
- Long random APP_API_KEY and exact CORS_ORIGINS.
- Licensed/official feed URLs for each source that is available to the account.
- Ollama endpoint reachable from backend and/or an OpenAI-compatible cloud endpoint plus server-side key.
- MAX bot token, channel ID and posting permission configured server-side.

Never commit real secrets, bot tokens, cloud AI keys or a real `.env` file.
