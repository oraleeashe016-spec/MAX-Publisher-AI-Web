# MAX Publisher AI Web — v0.2

Mobile-first PWA for preparing digital-technology deal posts for a MAX channel.

## v0.2 implemented

- Improved mobile-first dashboard and five-section navigation.
- Demo product catalog with text search, category chips, store filter, minimum-discount filter and sorting.
- Product-to-editor handoff with price, old price, product URL and draft text.
- Draft preview and editable publication queue.
- Draft persistence in browser local storage on the current device.
- JSON export for backup.
- Updated PWA manifest and versioned service-worker cache with old-cache cleanup.
- Honest integration states: providers, hybrid AI and MAX delivery are shown as not connected until real server credentials and adapters exist.

## Important: demo data

The product list, prices and discount percentages are illustrative demo data. They are not fetched from Yandex Market, Ozon, DNS, M.Video or Citilink and must not be published as current offers.

## Deploy

GitHub Pages deploys the repository root using `.github/workflows/pages.yml`.

Public URL: https://oraleeashe016-spec.github.io/MAX-Publisher-AI-Web/

After a new deployment, if an older page remains cached on a phone, close the installed PWA/browser tab and reopen the URL. The service worker uses a versioned cache and clears the previous cache on activation.

## Architecture for real integrations

GitHub Pages is a static host. It cannot safely store API secrets, run Ollama, or perform authenticated MAX Bot API delivery. Real operation requires a separate HTTPS backend.

Planned backend responsibilities:

1. Provider adapters for Yandex Market, Ozon, DNS, M.Video and Citilink, using only authorized APIs, affiliate feeds or licensed catalog providers.
2. Product normalization: source, product ID, model, current price, previous/reference price, availability, region, URL and checked-at timestamp.
3. Deal scoring that distinguishes a verified price history from a seller-provided crossed-out price.
4. Hybrid AI router: local Ollama where reachable by the backend, cloud provider as configured fallback, timeouts and cost controls.
5. MAX Bot API transport using the current official API contract, with channel permissions and explicit manual approval.
6. Owner authentication, rate limiting, audit log, HTTPS and server-side secret storage.

## Security

Never put API keys, bot tokens, or private credentials in browser JavaScript, this public repository, or a GitHub Pages deployment. Do not scrape private endpoints or bypass access controls.

## Local preview

Serve the repository root with any static HTTP server, or open the public Pages URL on a phone. Service-worker/PWA behavior requires HTTPS or localhost.
