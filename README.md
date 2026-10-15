# Umbraco local topology template

`UmbracoTopology.Template/` is a `dotnet new` template for a fresh Umbraco 17 solution with one CM, two CDs, a Single mode, a sample site, Aspire, and local MCP tooling. It uses Redis cache and Blob media by default. Choose either Redis or MSSQL cache independently of Blob or filesystem media.

AppHost includes Mailpit for local email. CM and Single send failed health checks to the selected admin address. Aspire Service Defaults adds traces, metrics, and health endpoints. Add `--reverse-proxy` for YARP host routing. Trust the .NET 10 development certificate for the default `*.dev.localhost` hosts. Custom hosts need a supplied certificate.

The current NuGet.org prerelease is `0.0.1-pre`. Install it with:

```bash
dotnet new install Casko.UmbracoTopology.Templates@0.0.1-pre
```

To use the template source from this repository, install it and generate a project:

```bash
dotnet new install ./src/UmbracoTopology.Template
dotnet new casko-umbraco-topology \
  --name Acme.UmbracoSite \
  --output ./Acme.UmbracoSite \
  --sql-password 'Dev1234567890!' \
  --cache-provider redis \
  --media-provider blob \
  --container-runtime podman \
  --admin-email admin@cm.dev.localhost \
  --admin-password 1234567890 \
  --api-user-email apiuser@dev.localhost \
  --api-client-id umbraco-back-office-api-user \
  --api-client-secret 1234567890 \
  --allow-scripts Yes
```

Set every scaffold option in one command:

```bash
dotnet new casko-umbraco-topology \
  --name Example.UmbracoSite \
  --output ./Example.UmbracoSite \
  --sql-password 'Dev1234567890!' \
  --cache-provider mssql \
  --media-provider filesystem \
  --container-runtime podman \
  --admin-email admin@cm.dev.localhost \
  --admin-password 'LocalAdmin!234' \
  --api-user-email apiuser@dev.localhost \
  --api-client-id umbraco-back-office-example \
  --api-client-secret 'LocalApi!234' \
  --cm-port 64222 \
  --cd-port 44222 \
  --proxy-port 4443 \
  --cm-domain cm.dev.localhost \
  --cd-domain cd.dev.localhost \
  --reverse-proxy \
  --allow-scripts Yes
```

Every scaffold option has a default. The second command sets them explicitly. Add `--reverse-proxy` to generate YARP. Use `--cm-port` and `--cd-port` for private HTTPS ports. CD2 uses the next CD port. Use `--proxy-port` for the shared public HTTPS port; its default is `4443`. Use `--cm-domain` and `--cd-domain` for public hosts; their defaults are `cm.dev.localhost` and `cd.dev.localhost`. The CLI runs `scripts/configure-scaffold.py` after generation. Run that script yourself if an IDE skips it. Custom API client IDs must start with `umbraco-back-office-`, as Umbraco requires. Empty credential options are rejected during generation. A custom SQL password must meet SQL Server's password policy; `scripts/validate-generated.py` checks it before startup. The passwords and secret are local development defaults. Passing custom values on the command line can expose them in shell history and process arguments. Generated credentials are kept in one ignored `.local/credentials.env` file and read by the AppHost, CM, Single, and the MCP setup script. That script writes separate ignored MCP configurations for Claude Code and Codex. The generated project's README has the run commands and its unique endpoints.

Run the generation and build matrix with `python3 .agents/skills/verify-umbraco-template/scripts/verify_template.py`. Add `--runtime` to boot each generated Cluster, verify published content and uploaded media on CM and both CDs, then restart in Single mode against the same SQL data. The runtime check also exercises MCP, Mailpit, proxy routing, and dashboard telemetry. This requires .NET 10, the Aspire CLI, Node.js, and Podman. Verification projects live in a temporary directory and are removed after the command completes.

Run the Docker based CI smoke test locally with `python3 .agents/skills/verify-umbraco-template/scripts/verify_template.py --single-smoke`. It starts one generated Single instance. It checks content, media, MCP, Mailpit, and telemetry. Use `--smoke-container-runtime podman` when testing with Podman. Cluster replication and YARP routing remain covered by `--runtime`.

For a versioned local package, run `dotnet pack src/UmbracoTopology.TemplatePack.csproj -c Release` and install the resulting `.nupkg` with `dotnet new install`.

GitHub Actions builds every template variant after any push. A separate workflow runs the Single smoke test with Docker after pushes to `main`. Publish a GitHub Release with a tag such as `v1.0.0` or `v1.0.0-beta` to publish the template to GitHub Packages and NuGet.org. Tags outside `main` require a prerelease suffix such as `-pre` or `-beta`. Set the `NUGET_USER` repository variable to your NuGet.org profile name. On NuGet.org, add a trusted publishing policy for repository owner `hallojoe`, repository `umbraco-topology`, and workflow file `publish.yml`. The NuGet.org push uses this policy without a stored API key.
