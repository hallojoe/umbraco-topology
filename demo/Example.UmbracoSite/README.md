# Example.UmbracoSite

Local Umbraco 17.7.1 topology on .NET 10 and Aspire 13.5.4. Cluster mode runs one `SchedulingPublisher` (CM) and two `Subscriber` (CD) processes. Single mode runs the same web project alone. Both modes use one SQL Server 2022 content database, `mssql` distributed cache, and `filesystem` shared media. AppHost includes Mailpit, DbGate, optional Redis Insight, optional Azurite, and a separate Astro frontend. Aspire Service Defaults sends web and proxy telemetry to the dashboard. A published sample site is imported by uSync on first boot.

## Prerequisites and setup

Install .NET 10, the Aspire CLI, Python 3, a container runtime, and Node.js 22 or newer. The AppHost Development launch profile is generated for the chosen `--container-runtime`; `auto` leaves Aspire to select the runtime. Trust a local ASP.NET Core HTTPS development certificate before starting the app. Run `python3 scripts/configure-scaffold.py` if your IDE skipped the template post-action.

From this directory, restore the solution, validate the generated credentials, install the pinned MCP package, and write ignored MCP client configurations:

```bash
dotnet restore Example.UmbracoSite.slnx
npm ci --prefix frontend
python3 scripts/validate-generated.py
npm ci --prefix mcp
python3 scripts/configure-mcp.py
```

The AppHost reads the SQL password chosen at template creation from the ignored `.local/credentials.env` file. Keep it unchanged while using the persistent `example-umbracosite-sql` volume. The SQL container stays running when the AppHost stops, so Cluster and Single reuse it; remove it with your container runtime when the local project is no longer needed. Blob media, when selected, persists in `example-umbracosite-azurite`. Shared data-protection keys, the imaging HMAC key, and filesystem media live under the web project's ignored `.local/umbraco` directory. Each process uses a separate temp directory and log filename.

The same credential file holds the administrator and API identity values selected at generation. Defaults are `LocalSql!1234567890` for SQL, `admin@cm.dev.localhost` / `1234567890` for the administrator, and `apiuser@dev.localhost`, client ID `umbraco-back-office-api-user`, and secret `1234567890` for the API user. A custom SQL password must be 8–128 characters and use at least three of uppercase, lowercase, digits, and symbols. Umbraco requires every API client ID to start with `umbraco-back-office-`. CM and Single read this file before first install; the MCP configuration reads the same client ID and secret. Changing an `AddIfMissing` value after provisioning does not rotate an existing API credential. Custom secrets supplied as `dotnet new` options may appear in shell history or process arguments; keep this topology on a disposable local development database.

## Run

```bash
# Cluster: CM, CD 1, and CD 2 start in sequence.
aspire start --launch-profile Development --non-interactive
aspire wait cm --non-interactive
aspire wait cd1 --non-interactive
aspire wait cd2 --non-interactive
aspire wait mailpit --non-interactive
aspire wait frontend --non-interactive
aspire describe --non-interactive
aspire stop --non-interactive

# Single: run only after stopping Cluster.
TopologyMode=Single aspire start --launch-profile Development --non-interactive
aspire wait single --non-interactive
aspire wait frontend --non-interactive
aspire stop --non-interactive
```

| Process | Website | Backoffice |
| --- | --- | --- |
| CM | https://cm.dev.localhost:4443/ | https://cm.dev.localhost:4443/umbraco |
| CD 1 | https://cd.dev.localhost:4443/ | Disabled |
| CD 2 | https://cd.dev.localhost:4443/ | Disabled |
| Single | https://localhost:24763/ | https://localhost:24763/umbraco |

The frontend has its own endpoint in the Aspire dashboard. It does not use the Umbraco proxy. Its pages come from `frontend/src/content/docs/`.

Private CD endpoints are https://localhost:44222/ and https://localhost:44223/. The Aspire dashboard shows the Mailpit inbox URL, health, traces, and metrics. AppHost supplies Mailpit's allocated SMTP host and port to each web process. CM and Single run health checks at startup and daily at 04:00 local time. Failed checks send email to the selected admin address. Mailpit captures all local mail.

`--cm-port` and `--cd-port` select private HTTPS ports. CD2 uses the next CD port. `--proxy-port` selects the shared public HTTPS port. `--cm-domain` and `--cd-domain` select public hosts when `--reverse-proxy` is enabled. Without explicit private ports, the template generates them. For default hosts, trust the .NET 10 development certificate with `dotnet dev-certs https --trust`. Custom hosts must resolve to loopback and need a certificate with both hostnames. Set `ASPNETCORE_Kestrel__Certificates__Default__Path` and `ASPNETCORE_Kestrel__Certificates__Default__Password` before starting Aspire. Port availability at generation time does not guarantee availability later.

## Frontend

From `frontend/`, run `npm run check`, `npm test`, `npm run build`, and `npm run test:e2e`. The browser test starts a preview of the built site. Run `npx playwright install chromium` once before browser tests.

Set `SITE_URL` to the public origin before a deployment build. Without it, the site uses `http://localhost:4321`. The local build blocks crawlers through `robots.txt`. Starlight generates the sitemap during the build.

## MCP and verification

The local `mcp/package-lock.json` pins `@umbraco-cms/mcp-dev` 17.6.10. `scripts/configure-mcp.py` reads the public CM URL and API credentials. For custom proxy certificates, set `NODE_EXTRA_CA_CERTS` to a PEM file before running it. It writes ignored `.mcp.json` for Claude Code and `.codex/config.toml` for Codex. Both contain the API secret; keep them private. Codex loads project configuration only for trusted projects. Restart Codex after configuration. Start the MCP client after CM is healthy. For Single, run `UMBRACO_BASE_URL=https://localhost:24763 python3 scripts/configure-mcp.py`; regenerate without that override when returning to Cluster. `node mcp/check.mjs` checks initialization, tool listing, and a read of the sample Home document.

Build the solution with `dotnet build Example.UmbracoSite.slnx`. In Cluster mode, verify the published Home and `/about/` pages on both CDs, then upload media through CM and check it on both CDs after restarting the AppHost. Test Single against the same persistent SQL and media. A healthy role endpoint or HTTP 200 at `/` alone does not prove content and media propagation.
