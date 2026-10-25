---
name: demo-astro-frontend
description: Maintain the detached Astro and Starlight frontend in demo/Example.UmbracoSite. Use for its pages, Markdown content, catalog behavior, SEO, accessibility, tests, or Aspire frontend resource.
---

# Demo Astro frontend

The site is in `demo/Example.UmbracoSite/frontend`. It is a static Astro site with Starlight and Vite.
It runs as a separate Aspire resource. Umbraco and YARP do not serve its pages.
Read the frontend `package.json`, `astro.config.mjs`, and `src/content.config.ts` before changes.
Use the Astro MCP in `.codex/config.toml` for uncertain framework details when it is available.

## Content and pages

- Keep site content in Starlight's `src/content/docs` Markdown and MDX collection.
- Preserve `/`, `/events/`, `/products/`, and `/about/`. Detail URLs come from content file paths.
- Give every page a title and description. Give events `eventDate` and products `publishedAt`.
- `src/lib/content.ts` reads items. `src/lib/catalog.ts` sorts upcoming events and newest products.
- Home shows two nearest upcoming events and two newest products. Preserve the empty-events message.
- Static builds fix the event list at build time. Rebuild when content or current dates change.
- Use Starlight navigation, layout, search, metadata, and sitemap before adding custom code.
- Set `SITE_URL` to the public origin for deployment. The local default is `http://localhost:4321`.
- Keep headings, link names, and image text accessible. Check the main routes after UI changes.

## Aspire and checks

- `Example.UmbracoSite.AppHost/AppHost.cs` calls `AddDemoFrontend()` in both topology modes.
- That method uses `AddViteApp("frontend", "../frontend")`, `PublishAsStaticWebsite()`, and `WithExternalHttpEndpoints()`.
- Keep the frontend separate from Umbraco and Delivery API until integration is requested.
- Keep `--ignore-lock` on the dev and preview scripts. It keeps Astro attached to Aspire and Playwright.
- From the frontend directory, run `npm ci`, `npm run check`, `npm test`, and `npm run build`.
- Run `npm run test:e2e` after route, navigation, or accessibility changes. Install Playwright Chromium if needed.
- For AppHost changes, also apply `aspire-apphost-conventions` and the installed Aspire workflow skill.
