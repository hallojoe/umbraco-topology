# Optional Redis distributed cache

Use this reference when the user requests Redis, or when converting a project already using Redis. Redis replaces the topology's SQL Server **distributed cache**, not Umbraco's SQL Server database. Do not register both distributed cache providers or create `dbo.DistributedCache` for a Redis choice.

For a new local topology, add the Aspire Redis hosting integration at the AppHost's existing Aspire version and model one `cache` resource with `AddRedis("cache")`. Reference it from CM, both Subscribers, and Single when Single runs. Ensure it is healthy before any dependent web process starts. Register the matching Redis distributed cache client in the web project using the `cache` connection supplied by Aspire. Keep the selection local to the topology when the project has other startup modes. Configure an actual Redis cache key namespace shared by these processes and distinct from unrelated local sites; for the .NET Redis distributed cache client, verify `RedisCacheOptions.InstanceName` or the selected provider's equivalent. `AddDataProtection().SetApplicationName(...)` does not set that Redis cache prefix. Continue to use SQL Server for `umbracoDbDSN` and Umbraco's own data.

On conversion, inspect the effective existing `IDistributedCache` registration and connection settings before editing. Preserve a working Redis provider and its configuration. If the user explicitly requests a switch from SQL cache, replace only the cache registration, remove local SQL cache initialization that is no longer used, and keep the database configuration intact. Do not delete an existing cache table or its data. If an existing external Redis service is configured, reuse it unless the request calls for an Aspire managed local instance.

Build and, when the local runtime is available, confirm that all three processes connect to the same Redis resource and content changes propagate to both Subscribers. Document the chosen provider and any required local connection settings without exposing secrets.

- [Aspire Redis hosting and connection](https://aspire.dev/integrations/caching/redis/redis-connect/)
- [Aspire Redis distributed cache client](https://aspire.dev/integrations/caching/redis-distributed/redis-distributed-get-started/)
- [Umbraco load balancing](https://docs.umbraco.com/umbraco-cms/17.latest/run-in-production/infrastructure-and-ops/server-setup/load-balancing.md) (use the selected major's documentation)
