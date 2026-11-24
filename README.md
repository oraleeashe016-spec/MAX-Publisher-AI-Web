# MAX Publisher AI Web

Mobile-first PWA prototype for finding digital-tech offers and preparing MAX channel posts.

## Included
- Responsive mobile interface and bottom navigation
- Demonstration product catalog with store and discount filters
- Product-to-post editor, draft text template, preview and queue
- PWA manifest and basic service-worker cache
- GitHub Actions workflow for GitHub Pages deployment

## Important
Catalog items and prices are illustrative demo data, not live store offers. No store API, AI provider, or MAX Bot API is connected yet. Do not publish demo data as real discounts.

## Deployment
In repository Settings → Pages, select **GitHub Actions** as the build and deployment source if it is not already selected. The workflow deploys the repository root on pushes to `main`.

## Next steps
Implement permitted adapters for Yandex Market, Ozon, DNS, M.Video and Citilink; hybrid Ollama/cloud AI; secure backend secrets; and MAX Bot API transport with explicit confirmation and audit logging.
