# Local Umbraco topology

Use this reference for both create and convert on Umbraco 17 or newer after checking the selected major's APIs. The topology is for development on one machine, with one Umbraco web project run three times from the same source. The three processes share one SQL Server database and media store. They must not share temporary storage or log filenames.

## Roles and launch profiles

Register a role implementation verified for the selected Umbraco major with the Umbraco builder, reading `UMBRACO_SERVER_ROLE` and defaulting to `Single`. For compatible versions, use `Casko.SyncExtensionsForUmbraco`. Validate that the value is exactly `Single`, `SchedulingPublisher`, or `Subscriber` before calling `AddServerRole(role)`; the package may fall back to `Single` for an unknown value. Keep the template's existing Umbraco services and middleware. Do not build a second Umbraco pipeline.

For package `Casko.SyncExtensionsForUmbraco` **1.0.0-pre**, the NuGet metadata points to [this exact source revision and registration API](https://github.com/hallojoe/sync-extensions-for-umbraco/blob/326b6992023e2c3c9e5b480fc7028f5fb8a32cda/src/Casko.SyncExtensionsForUmbraco/Configuration/UmbracoBuilderExtensions.cs). The repository's main README uses the singular package spelling; use the package ID and namespace from the selected release. The package declares Umbraco CMS 17.6.2 dependencies. A minimal registration within the template's existing Umbraco builder chain is:

```csharp
using Casko.SyncExtensionsForUmbraco.Configuration;

var role = builder.Configuration["UMBRACO_SERVER_ROLE"] ?? "Single";
if (role is not ("Single" or "SchedulingPublisher" or "Subscriber"))
    throw new InvalidOperationException($"Unknown Umbraco server role: {role}");

builder.CreateUmbracoBuilder()
    .AddServerRole(role)
    .AddBackOffice()
    .AddWebsite()
    .AddComposers()
    .Build();
```

Keep any other template registrations in that same builder chain. Recheck the API against the chosen package version before copying this 17.6.2 example into another major.

Use valid `launchSettings.json` (no comments or missing commas). Preserve any existing profile names on conversion; if one of the suggested names already means something else, choose an unoccupied name and use it consistently in AppHost. Suggested defaults:

| Role | Profile suffix | HTTPS | HTTP | Application URL without YARP |
| --- | --- | --- | --- | --- |
| Single | `Single` | `24101` | `23101` | `https://localhost:24101/` |
| CM | `SchedulingPublisher` | `64101` | `54101` | `https://localhost:64101/` |
| CD 1 | `Subscriber1` | `44101` | `34101` | `https://localhost:44101/` |
| CD 2 | `Subscriber2` | `44102` | `34102` | `https://localhost:44102/` |

Each profile uses `commandName: Project`, `ASPNETCORE_ENVIRONMENT: Development`, its role, unique `applicationUrl`, and `Umbraco__CMS__WebRouting__UmbracoApplicationUrl` matching its public URL. CM's `Umbraco__CMS__Security__BackOfficeHost` is its public CM origin; set it to an empty string in each Subscriber profile. Set `ConnectionStrings__umbracoDbDSN_ProviderName=Microsoft.Data.SqlClient` for the CM/CD profiles, and for Single when it uses the same SQL database. If a suggested port is already owned by an existing profile or local service, choose a different free port and update every dependent setting.

Declare the local temp and logging settings in `launchSettings.json` for **each** CM, CD, and Single profile, plus the role-specific Examine setting for CM and both CDs. Startup code may resolve portable relative paths to absolute paths and create directories, but must honor the profile values rather than silently replacing them. Never persist the creator's machine-specific absolute paths. Use the following profile contract for a new topology; adjust directory names to fit the project while keeping the relationships intact:

Create the configured temp directories **before Aspire launches each project**. The `dotnet run` launcher itself uses `TEMP`/`TMP`/`TMPDIR`; if a relative profile path does not exist in its working directory, the process can fail with `Unable to find the specified file` before `Program.cs` executes. AppHost directory preparation may be needed in addition to startup path resolution. Keep the launch-profile values as the source of truth and verify the effective working directory rather than assuming it is the web content root.

| Setting | CM | CD 1 | CD 2 | Single |
| --- | --- | --- | --- | --- |
| `TEMP`, `TMP`, `TMPDIR` | Same CM-only path | Same CD 1-only path | Same CD 2-only path | Same Single-only path |
| `Umbraco__CMS__Hosting__LocalTempStorageLocation` | `EnvironmentTemp` | `EnvironmentTemp` | `EnvironmentTemp` | `EnvironmentTemp` |
| `Umbraco__CMS__Examine__LuceneDirectoryFactory` | `SyncedTempFileSystemDirectoryFactory` | `TempFileSystemDirectoryFactory` | `TempFileSystemDirectoryFactory` | No override required; preserve an existing Single setting on conversion |
| `Umbraco__CMS__Logging__Directory` | Shared ignored local log path | Same log path | Same log path | Same log path |
| `Umbraco__CMS__Logging__FileNameFormat` | Unique CM name with `{0}` | Unique CD 1 name with `{0}` | Unique CD 2 name with `{0}` | Unique Single name with `{0}` |

Verify the Examine setting names and factory values against the selected Umbraco major before writing them. The CM factory keeps a local Lucene index and syncs it to the main index storage; each Subscriber's factory uses only that process's temp storage. These choices are part of this local CM/CD topology for both disk and Blob media. Do not omit them merely because the media provider is Blob. Do not reuse a temp path or log filename across processes.

Choose the media profile setting by provider:

- **Disk media:** Put `Umbraco__CMS__Global__UmbracoMediaPhysicalRootPath` in every local profile, including Single. Its value resolves to the **same** shared, ignored media directory for all processes. Media must not have a per-instance path.
- **Blob media:** Omit `Umbraco__CMS__Global__UmbracoMediaPhysicalRootPath` from the local profiles. Configure one shared Blob container through [media.md](media.md); do not register a competing disk media root.

On conversion, preserve unrelated profiles and existing storage choices. Inspect existing local profile values before changing them, and reconcile any deliberate Examine or path customization with the CM/CD contract rather than overwriting it without review.

## Shared local state

- Use `AddDataProtection().SetApplicationName(...)` and `PersistKeysToFileSystem(...)` with one stable application name and one shared ignored local key directory derived from the web project's content root. This supports cookies across both CDs. Keep the key directory outside per-instance temp folders.
- Supply one stable `Umbraco:CMS:Imaging:HMACSecretKey` to every instance through untracked local configuration. A fresh unattended install may generate this key and write it to `appsettings.json`; inspect the file after installation and move any generated key out of tracked configuration. Keep the same key across restarts so signed image URLs remain valid. On conversion, preserve the existing effective key and its storage rather than replacing it.
- By default, register SQL Server distributed cache for all CM/CD processes using the existing `umbracoDbDSN` connection. Create the `dbo.DistributedCache` table and expiry index idempotently before the web processes start; do not replace or migrate Umbraco tables. For Redis, follow [cache.md](cache.md) and do not create the SQL cache table. On conversion, retain any working distributed cache provider already configured unless the user requests a change.
- For disk media, place shared media and key directories, plus temp and log directories, under an ignored local development root such as `.local/umbraco`. Exclude generated data from source control. Existing shared media storage takes precedence on conversion.

## Aspire and installation

For a new project, create a C# AppHost with `Aspire.Hosting.SqlServer`. Use SQL Server image tag `2022-latest`, a persistent data volume, and an `umbracoDbDSN` database resource. Reference that database from CM and both CDs so Aspire injects the connection string; set the provider name to `Microsoft.Data.SqlClient`. Give the SQL resource a stable password from an untracked local secret or Aspire secret parameter. SQL Server retains the `sa` password in its persisted data; a newly generated password on a later Aspire run can leave the resource unable to reopen the volume. Document how to set the secret once and retain it across restarts and mode switches. Use startup dependencies so SQL is ready before CM and CM is ready before the CDs. For the default SQL cache, make table initialization idempotent and complete before any web process uses it. Do not hardcode a SQL password in tracked files. Use the existing Aspire version if adding to a solution that already has it; otherwise use a version compatible with the selected Umbraco target framework and installed SDK, verifying its current APIs. If using `aspire new` inside a project with its own agent skills, pass `--suppress-agent-init` to avoid writing over those skills. Keep the AppHost's normal CLI bundle support; do not disable it merely to bypass an isolated test's NuGet restrictions. Honor the developer's container runtime rather than assuming Docker. When the developer uses Podman, set `ASPIRE_CONTAINER_RUNTIME=podman` in the AppHost's Development launch profile, document it, and check that the Podman service is running.

For conversion, create or extend an AppHost that starts the three web profiles but leaves the existing SQL connection configuration in place. Do not add an Aspire SQL container or overwrite user secrets. Document how the existing SQL Server must be reachable from each process. If an AppHost already models that same database, reuse its resource and references.

Retain `Single` as a runnable alternative: in a new AppHost, allow an explicit single-mode run against the same SQL resource rather than starting CM/CD simultaneously with Single. On conversion, keep the project's current single-instance run path and connection configuration.

For a fresh database only, enable unattended installation in **Development** on CM (and Single when run alone). Use `UnattendedUserName=Administrator`, `UnattendedUserEmail=admin@example.com`, `UnattendedUserPassword=1234567890`, and `InstallUnattended=true`. Do not configure additional language installation. Do not add or reset users on conversion, or enable unattended install on CD profiles. Document the fixed development credentials clearly; never copy them into production settings. Ensure the CM completes initial database installation before CDs start. If an Aspire readiness dependency proves insufficient, use a readiness check tied to Umbraco boot completion.

For a fresh topology, a local-only readiness endpoint mapped after `BootUmbracoAsync()` can report the effective role through `IServerRoleAccessor.CurrentServerRole`. Add an Aspire HTTP health check for that endpoint and make both CDs wait for CM health, not just its process start. Reporting only the configured `UMBRACO_SERVER_ROLE` value does not verify that Umbraco registered the intended role. Avoid adding a diagnostic endpoint to converted or nonlocal configurations unless it fits their existing conventions.

Inspect Aspire resource state before testing URLs. When recording diagnostics, select state, health, and URLs from `aspire describe --format Json`; a full resource description can include environment secrets. After a rapid Podman stop and mode switch, a SQL container may briefly exit while its prior process releases the persistent volume. Check its logs and use `aspire resource <sql-resource-name> start --non-interactive` when that is the cause, then wait for health through Aspire before concluding that the volume or password is broken.

Apply local-only paths, cache wiring, and installation settings only when the local topology is selected. Preserve the generated project's normal startup behavior in other environments; do not make production startup fail merely because `ASPNETCORE_ENVIRONMENT` is not `Development`.

## Completion checks

Build the complete solution. Parse the resulting `launchSettings.json`: check all four local profiles have three instance-specific temp variables, `EnvironmentTemp`, a log directory, and unique log filenames containing `{0}`; check the CM and both CDs have the role-specific Examine factory, correct role and URL, and expected backoffice host. For disk media, check all four profiles resolve to one shared physical media root; for Blob media, check no profile sets that root and all instances use the shared Blob provider. Confirm that startup code does not override these values. If the local environment supports it, start the AppHost, check effective roles and paths, publish content in CM, and check both CDs serve that content and media. For a new simple site, request a known child page such as `/about/` on each CD as well as Home: a healthy role endpoint and a rendered Home did not expose a stale child route on one CD in a 17.7.1 first-boot trial. Investigate any mismatch, retest after the affected resource and full AppHost restart, and report it. Restart the AppHost against the same persistent SQL volume and test `Single` separately; resource health on the first run does not prove either restart works. Check that generated secrets, including the imaging key, did not enter tracked files.

On a fresh unattended install, a `200` response from a CD root may be Umbraco's **No Published Content** page. It proves URL reachability, not content propagation. If no document or media has been created, report those checks as unverified and give the developer concrete steps to publish and inspect them. Report meaningful restore warnings, including NuGet security advisories, separately from build success. Before pinning a newer transitive package to address an advisory, check whether it actually resolves the advisory and whether it changes compatibility or licensing.
