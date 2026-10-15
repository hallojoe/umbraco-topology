# uSync and local Umbraco MCP

Apply this default to new local topologies and SQL Server conversions unless the user opts out. Work with the effective Umbraco version and existing package/configuration conventions. Do not silently change the Umbraco major or a converted site's existing uSync data or API users.

## Web packages and first boot

- Add the stable `uSync` NuGet release whose major matches the web project's Umbraco major. Verify its dependency minimum against the selected CMS version before editing. Add `uSync.Command.Setup` separately: `uSync` by itself does not create the API user from `uSync:Command:AddIfMissing`. Verify a setup release that restores and works with the exact CMS version; its version does not necessarily track the uSync major. For example, `uSync.Command.Setup` 17.0.0 requires `Umbraco.Cms.Web.Common` 17.6.2 or newer. If no compatible setup release exists, report the blocker rather than upgrading Umbraco or claiming the API user will exist.
- For a new project, copy the `$umbraco-simple-site` assets before first boot, then enable `uSync:Settings:ImportOnFirstBoot` on the CM launch profile and on Single when it runs alone. Leave `FirstBootGroup` at its `All` default or set it to `All` so the snapshot's templates, document types, and published content all import; `Settings` alone omits the pages. This is a one-time import, not a recurring startup import. Keep it off both Subscribers. On conversion, preserve existing uSync settings and files. Check whether enabling first boot would import tracked files into an existing database before setting it to true. Do not overwrite a deliberate existing uSync configuration.
- Put the development-only values below in `Properties/launchSettings.json` as **environment variables** for CM and Single. The `__` form is translated to nested configuration by the ASP.NET Core environment variable provider; literal `__` keys in `appsettings.json` do not provide the same structure. Environment variable values, including booleans, are strings in launch settings. Use role-specific overrides or equivalent existing local configuration when converting, and keep API user creation off both Subscriber profiles.

```json
{
  "uSync__Settings__ImportOnFirstBoot": "true",
  "uSync__Command__AddIfMissing": "true",
  "uSync__Command__Name": "API User",
  "uSync__Command__Username": "api-user@example.com",
  "uSync__Command__Email": "api-user@example.com",
  "uSync__Command__Secret": "1234567890",
  "uSync__Command__ClientId": "umbraco-back-office-api-user"
}
```

- These fixed credentials are for an isolated local development database only. Provide a documented override that takes precedence over the launch profile default and supplies the same effective secret to CM and MCP; verify the precedence instead of assuming user secrets override launch-profile environment variables. `AddIfMissing` creates a missing API user; changing the configured secret later does not rotate an existing user's credential. Do not print the secret in logs. Ensure the API user has a group with the permissions needed for the selected MCP tool collections. Wait for CM to finish installation and provisioning before starting Subscribers or connecting MCP. Check creation and authentication on a fresh database and idempotence on a second boot; a successful build alone proves neither.

## Project-local MCP

- Use the official `@umbraco-cms/mcp-dev` npm package matching the Umbraco major. Check the published version and `engines.node` for that major; do not use `latest` for a 17 site or assume a release exists for every future major. Create a small project-local npm package, install the chosen exact version, commit `package.json` and `package-lock.json`, then run `npm ci` as part of project setup. Do not assume a global MCP installation. Node itself must meet the selected package's engine requirement.
- Configure the intended MCP client to launch the installed local executable over stdio from the correct project directory. If no client is named, configure one available local client and identify it in the run instructions. Verify its command working directory and path rules; if those require an absolute path, generate an ignored local client config rather than committing a machine-specific path. Set `UMBRACO_BASE_URL` to the CM endpoint (or Single when that is the active mode), `UMBRACO_CLIENT_ID=umbraco-back-office-api-user`, and `UMBRACO_CLIENT_SECRET` to the same effective development secret used by the web project. Select a bounded set of `UMBRACO_INCLUDE_TOOL_COLLECTIONS` appropriate to the API user's permissions. Keep local secret files ignored; a generated client config may use the fixed development default only for the disposable local database.
- Start Aspire to run Umbraco, then connect the MCP client; the client starts the local Node process. Merely adding a stdio Node process to Aspire does not make it connectable by an MCP client. If the user requests Aspire-managed MCP, implement and verify a local HTTP MCP transport/bridge and give the client its actual endpoint; do not call an unconnected stdio process complete. Test client-credentials authentication over the browser-facing HTTPS CM URL: Umbraco's backoffice token endpoint rejected plain HTTP in the verified 17.7.1 setup. Avoid disabling TLS verification globally. In `@umbraco-cms/mcp-dev` 17.6.10, its SDK sets `NODE_TLS_REJECT_UNAUTHORIZED=0` when `NODE_ENV` is not `production`; a verified local client ran with `NODE_ENV=production` and `NODE_USE_SYSTEM_CA=1` against a certificate trusted by the host. In that Linux trial, setting only `NODE_EXTRA_CA_CERTS` still failed the Node handshake. Recheck this behavior for the selected MCP version and choose a trusted-certificate setup appropriate to the local Node runtime.
- If using the MCP server's `filePath` media upload for a local smoke test, set `UMBRACO_ALLOWED_MEDIA_PATHS` to an ignored, narrow test directory; without it the server rejects the upload. Do not grant the entire workspace merely to run the check.
- Verify `npm ci`, the client's MCP initialization and `tools/list`, and one permission-appropriate read-only tool against the running CM. Document the Node prerequisite, local setup command, client connection, URL, and development credentials. Do not claim MCP integration is working from an installed npm package alone.

## Sources to recheck

- [uSync versions](https://docs.jumoo.co.uk/usync/uSync/versions/)
- [uSync FirstBoot](https://docs.jumoo.co.uk/usync/uSync/guides/firstboot/)
- [uSync.Command.Setup API user](https://docs.jumoo.co.uk/usync/command/APIuser/)
- [uSync.Command.Setup 17.0.0 NuGet metadata](https://www.nuget.org/packages/uSync.Command.Setup/17.0.0)
- [Umbraco Developer MCP setup and compatibility](https://docs.umbraco.com/umbraco-in-ai/17.latest/mcp/mcp-servers/cms-developer-mcp.md) (switch to the selected Umbraco major)
