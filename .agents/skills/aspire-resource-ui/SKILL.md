---
name: aspire-resource-ui
description: Add a local management UI when adding a supported resource to a C# Aspire AppHost. Use for SQL Server, Redis, PostgreSQL, MySQL, MongoDB, RabbitMQ, Kafka, Milvus, SQLite, or Elasticsearch resources.
---

# Aspire resource UIs

Apply this skill alongside the installed Aspire skills when adding one of these resources to a C# AppHost. Use the project's installed Aspire version and package conventions to select compatible APIs and package versions.

| Resource being added | Local management UI | Method on its resource builder |
| --- | --- | --- |
| SQL Server | DbGate | `WithDbGate()` |
| Redis | Redis Insight | `WithRedisInsight()` |
| PostgreSQL | pgAdmin | `WithPgAdmin()` |
| MySQL | phpMyAdmin | `WithPhpMyAdmin()` |
| MongoDB | Mongo Express | `WithMongoExpress()` |
| RabbitMQ | Management UI | `WithManagementPlugin()` |
| Kafka | Kafka UI | `WithKafkaUI()` |
| Milvus | Attu | `WithAttu()` |
| SQLite | SQLiteWeb | `WithSqliteWeb()` |
| Elasticsearch | Elasticvue | `WithElasticvue()` |

Add the UI on the parent server builder after creating it and before any `AddDatabase` call. For SQLite, use the builder returned by `AddSqlite`. Put the UI call inside an `if (builder.ExecutionContext.IsRunMode)` block. Keep the resource builder available to `AddDatabase`, `WithReference`, and other calls in both run and publish modes. For example:

```csharp
var cache = builder.AddRedis("cache");
if (builder.ExecutionContext.IsRunMode)
{
    cache.WithRedisInsight();
}
```

The same pattern applies when a resource is declared inside an `IDistributedApplicationBuilder` extension method, including one that returns a database builder. Preserve its return type, resource name, dependencies, and other configuration. If the new resource already has a management UI, keep that choice under the run-mode guard instead of adding the default. Honor an explicit request to omit the UI or choose a different one. Do not retrofit unrelated existing resources.

For SQL Server, add `CommunityToolkit.Aspire.Hosting.SqlServer.Extensions` to the AppHost for `WithDbGate()`. For Elasticsearch, add `CommunityToolkit.Aspire.Hosting.Elasticsearch.Extensions` for `WithElasticvue()`. SQLite and `WithSqliteWeb()` use `CommunityToolkit.Aspire.Hosting.Sqlite`. The other UI methods are in their resources' hosting integrations. Add packages only when needed, following the project's existing package management style.

After editing an AppHost, build it and verify that each new supported resource has exactly one UI in run mode and none in publish mode. Check that resource references and names remain intact.
