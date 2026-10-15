---
name: umbraco-local-topology
description: Create an Umbraco 17 or newer local Aspire CM/CD topology with a simple site, or convert an existing SQL Server project. Includes uSync and a project-local Umbraco MCP, with optional Redis cache, Azure Blob media, or YARP; not for production deployment or product add-ons.
---

# Umbraco local topology

Build a runnable local Umbraco setup from one web project. The default Aspire topology runs one content management (CM) `SchedulingPublisher`, two content delivery (CD) `Subscriber` processes, SQL Server 2022 or later, SQL Server distributed cache, and shared local disk media. For a new project, include the packaged simple site from `$umbraco-simple-site` so the first run has published pages. Add matching uSync and a locally provisioned API user, plus a project-local Umbraco Developer MCP package for an MCP client to launch. Keep a usable `Single` profile for local single-instance work. Redis cache, Azure Blob media with local Azurite, and YARP are independent options. Apply the project's existing names, package management convention, and Aspire version when present.

## Choose a workflow before editing

Read [workflows.md](references/workflows.md) for create or convert. Honor a requested Umbraco version; otherwise prefer an installed 17+ template. Before converting, identify the effective Umbraco major and database provider. Stop without edits for versions below 17 or SQLite; preserve the existing SQL Server database and unrelated profiles.

## Configure and validate

Read [topology.md](references/topology.md) for role registration, launch settings, installation, and AppHost requirements. Use `Casko.SyncExtensionsForUmbraco` for explicit roles only after verifying its package and API work with the selected Umbraco major; the 1.0.0-pre release declares Umbraco 17 dependencies. For a newer major, test compatibility or use a verified version-specific role implementation. If neither works, stop with the specific compatibility issue instead of generating a broken topology. Do not copy unrelated features from the nearby reference app.

Read [usync-mcp.md](references/usync-mcp.md) for the default uSync package, development-only API user settings, and locally installed MCP package. Verify package compatibility before editing. Provision the API user on CM or Single, and have the MCP client launch the project-local Node package after CM is healthy. An Aspire-managed stdio process alone cannot accept a client connection; use an Aspire resource for MCP only when a working HTTP MCP transport is explicitly implemented and verified.

For a new project, use `$umbraco-simple-site` to copy its packaged uSync snapshot and Razor views into the selected web project before the first CM or Single boot. Follow that skill's collision checks; do not overwrite existing assets without an explicit request. Configure uSync's one-time first-boot import to include both settings and content, and run it only on CM or Single. A conversion keeps its existing content and views; add the sample site only when the user explicitly requests it.

Put the local instance's temp, logging, and Examine choices in each generated CM/CD launch profile, even if startup code resolves relative paths. For disk media, put the same shared physical media root in every local profile; for Blob media, omit that physical-root setting and use the shared Blob provider. Validate these profile values before treating a build or healthy resources as completion.

Choose cache and media independently. Infer an explicit Redis or Blob preference from the user's request; otherwise use SQL Server distributed cache and shared disk media. Ask only if the request is genuinely ambiguous. For Redis, read [cache.md](references/cache.md). For Blob media, read [media.md](references/media.md). On conversion, inspect existing cache and media providers and preserve them unless the user requests a change. Do not install Umbraco Search, Automate, or AI merely because this topology skill runs; each has its own skill.

For optional proxy work, also read [reverse-proxy.md](references/reverse-proxy.md). Follow the installed Aspire skill for AppHost lifecycle and `aspire-apphost-conventions` when available for resource organization. Neither changes this skill's topology decisions.

Build the solution. Use the developer's configured Aspire container runtime; `ASPIRE_CONTAINER_RUNTIME=podman` selects Podman when that is their choice. When the selected runtime and a suitable certificate are available, run Aspire and verify that CM installs first, all three processes report their assigned roles, CM and CD serve their URLs, the API user can authenticate, the project-local MCP can connect, list tools, and read a document, the simple site's Home and a known child page appear on both CDs for a new project, published content and media appear on both CDs after restart, and the proxy distributes CD requests if enabled. Keep local-only smoke media exports out of the tracked uSync snapshot. Record any runtime checks the environment prevents. Update local run instructions with commands, addresses, credentials, Node prerequisite, and prerequisite SQL/certificate setup. Never claim a runtime check passed from a successful build alone.

## Sources to recheck when APIs change

- [Umbraco installation](https://docs.umbraco.com/umbraco-cms/17.latest/get-started/installation.md) (switch documentation version to match the project)
- [Umbraco load balancing](https://docs.umbraco.com/umbraco-cms/17.latest/run-in-production/infrastructure-and-ops/server-setup/load-balancing.md) (switch documentation version to match the project)
- [Umbraco file system guidance](https://docs.umbraco.com/umbraco-cms/17.latest/run-in-production/infrastructure-and-ops/server-setup/load-balancing/file-system-replication.md) (switch documentation version to match the project)
- [Aspire SQL Server integration](https://aspire.dev/integrations/databases/sql-server/sql-server-get-started/)
