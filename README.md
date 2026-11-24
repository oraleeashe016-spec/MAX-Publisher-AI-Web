# MAX Publisher AI Web — v0.5.1

Mobile-first PWA for discovering technology stories and preparing posts for a MAX channel.

## v0.5.1 — RSS reliability and deployment readiness

- Search screen has two modes: product offers and RSS editorial content.
- Seven public RSS feeds are included from iXBT, 3DNews and Overclockers.ru.
- RSS search supports text filtering and selecting an individual feed.
- Articles can be transferred into the post editor with title, summary, publication date and source link.
- RSS items are clearly marked as editorial material, not prices, stock status or verified discounts.
- RSS feeds are fetched by the backend from a fixed allowlist; arbitrary user-supplied feed URLs are not fetched.
- RSS requests run concurrently with bounded connections.
- RSS responses are streamed with a 2 MB cap and redirects are rejected.
- Backend test coverage includes RSS parsing, filtering, input validation and secret-safe config.
- PWA cache version remains v0.4; the visible web edition version is maintained separately in `index.html`.

## Included open RSS sources

- iXBT News — https://www.ixbt.com/export/news/rss.xml
- iXBT Articles — https://www.ixbt.com/export/articles/rss.xml
- 3DNews Hardware — https://3dnews.ru/news/rss/
- 3DNews Software — https://3dnews.ru/software-news/rss/
- 3DNews Phones — https://3dnews.ru/phone/rss/
- Overclockers News — https://overclockers.ru/rss/news.rss
- Overclockers Lab / Reviews — https://overclockers.ru/rss/lab.rss

These feeds are public editorial feeds. Feed availability and publication frequency can change; the backend reports individual feed errors rather than claiming every source is always online. Respect publisher terms when quoting or reusing article text.

## Backend endpoints

- GET /api/health
- GET /api/config
- POST /api/search — configured authorized product JSON feeds
- GET /api/rss/feeds — allowlisted RSS feed directory
- GET /api/rss/items?query=&source=&limit= — read RSS items
- POST /api/ai/draft — hybrid Ollama/cloud drafting, requires X-API-Key
- POST /api/max/publish — explicit confirmed MAX publication, requires X-API-Key

## Important distinctions

RSS is useful for technology news, announcements and reviews. It is not a substitute for store price feeds and does not prove a product is discounted or available. Keep product-price ingestion and editorial RSS as separate modes.

GitHub Pages hosts only the static frontend. RSS parsing, AI calls and MAX delivery run on the separate FastAPI backend. Store API credentials, AI keys and MAX bot tokens only in backend environment variables.


## Deploy the backend on Render

The repository includes a Render Blueprint in `render.yaml`. To create the service, sign in to Render, create a new Blueprint deployment from this repository, and review the service settings before confirming. Render generates `APP_API_KEY`; keep it private. After the service is live:

1. Open `https://<your-render-service>.onrender.com/api/health` and confirm it returns `status: ok`.
2. Open `/api/config` and confirm the seven RSS feeds are listed in the backend directory and the MAX/AI providers are reported as unconfigured until credentials are added.
3. In the web app, open Settings, enter the backend HTTPS base URL and the generated `APP_API_KEY`, then choose “Проверить API”.
4. Search RSS mode and verify that current feed entries load. A feed may temporarily fail; the API reports per-feed errors.
5. Add AI and MAX credentials only in Render environment variables. Never put them in GitHub Pages, frontend source, issues or chat messages.

The free Render service may sleep while idle; the first request after inactivity can take longer. Live RSS checks, AI calls and MAX publishing cannot be marked verified until the Render service and the relevant credentials are configured.
