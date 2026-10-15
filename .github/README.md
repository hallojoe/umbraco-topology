# Umbraco! Aspire! AI-ready! Let's build!

**One template. A complete local CM/CD topology. Your next Umbraco project starts running.**

Stop wiring the same development setup together again. Generate a solution with content management, two delivery nodes, shared services, and a published sample site. Start the cluster with Aspire. See the whole system work.

## Look at what you get

- **A real local cluster:** One CM, two CDs, and a Single mode for focused work.
- **Content on first boot:** uSync imports a published sample site with Home and child pages.
- **Your choice of infrastructure:** Select Redis or MSSQL cache. Select Blob or filesystem media independently.
- **One place to run it:** Aspire starts the web processes, SQL Server, Mailpit, and selected local services.
- **See what happens:** Aspire collects web traces, metrics, and logs in one dashboard.
- **Public routes on demand:** Add YARP for CM and CD domains. Set private and public ports when you generate the project.
- **A clean handoff to AI tools:** A local API user and pinned Umbraco MCP package support Codex and Claude Code.
- **Proof you can run:** A verification skill builds eight combinations and checks live routing and email.

## From template to topology

```bash
dotnet new install ./src/UmbracoTopology.Template
dotnet new casko-umbraco-topology --name Acme.UmbracoSite --output ./Acme.UmbracoSite --allow-scripts Yes
cd Acme.UmbracoSite
python3 scripts/validate-generated.py
aspire start --launch-profile Development --non-interactive
```

That's it. The default setup uses Redis cache, Blob media, and Podman. Pass `--container-runtime docker` if Docker is your local runtime. The generated README gives you the URLs and run commands.

## AI-ready means ready to connect

The template provisions a local API user. It includes a pinned Umbraco Developer MCP package. One script writes ignored MCP configurations for Codex and Claude Code:

```bash
npm ci --prefix mcp
python3 scripts/configure-mcp.py
```

Start your MCP client after CM is healthy. Your agent can then use the configured document and media tools. The credentials stay in ignored local files.

## Build with confidence

Run the repository's [verification skill](../.agents/skills/verify-umbraco-template/SKILL.md) to generate, inspect, and build every provider combination. Add `--runtime` for live content, media, restart, and MCP checks.

**Build the site. Run the cluster. Connect your AI tools. Keep moving!**

This template targets local development. See the [project guide](../README.md) for prerequisites and full setup details.
