---
name: aspire-apphost-conventions
description: Organize new or changed C# Aspire AppHost resources in descriptively named builder extension methods. Use when editing AppHost resource declarations, not for runtime operations or TypeScript AppHosts.
---

# Aspire AppHost conventions

Apply these conventions alongside the installed Aspire skills when adding or changing resource declarations in a C# AppHost. Let the Aspire skills and the project's installed Aspire version determine the correct APIs and operational workflow.

- Put each new resource's creation and resource-specific configuration in an extension method on `IDistributedApplicationBuilder`. Give the method a name that describes the resource's role, such as `AddCatalogDatabase` or `AddOrdersApi`, rather than its implementation alone.
- Keep the AppHost entry point as a readable composition of these methods and `Build().Run()`. Accept dependencies as typed parameters when a resource needs references to other resources.
- Return the resource's `IResourceBuilder<T>` when callers need to configure or reference it. Preserve resource names, dependency edges, endpoint settings, configuration, and publish behavior when extracting existing code.
- Follow the project's existing namespace and file organization. Do not reorganize unrelated resource declarations or create a separate hosting integration solely to extract a local AppHost method.
- After editing, build the AppHost and check that the resource graph and references still express the requested topology.

For example, prefer `var database = builder.AddCatalogDatabase();` in the AppHost, with the `AddCatalogDatabase` extension containing its Postgres and database configuration. Keep the return type compatible with `WithReference(database)` where that reference is needed.
