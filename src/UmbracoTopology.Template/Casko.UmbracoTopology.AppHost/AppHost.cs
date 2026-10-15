using System.Text.Json;
using Aspire.Hosting.ApplicationModel;
#if MEDIA_BLOB
using Aspire.Hosting.Azure;
#endif

var builder = DistributedApplication.CreateBuilder(args);

var database = builder.AddUmbracoDatabase();
var mailpit = builder.AddMailPit("mailpit");
#if CACHE_REDIS
var cache = builder.AddSharedCache();
#endif
#if MEDIA_BLOB
var blobs = builder.AddSharedMediaStore();
#endif

string mode = builder.Configuration["TopologyMode"] ?? "Cluster";
if (mode == "Single")
{
    builder.AddUmbracoInstance("single", "Single", database, mailpit
#if CACHE_REDIS
        , cache
#endif
#if MEDIA_BLOB
        , blobs
#endif
    );
}
else if (mode == "Cluster")
{
    var cm = builder.AddUmbracoInstance("cm", "SchedulingPublisher", database, mailpit
#if CACHE_REDIS
        , cache
#endif
#if MEDIA_BLOB
        , blobs
#endif
    );
    var cd1 = builder.AddUmbracoInstance("cd1", "Subscriber1", database, mailpit
#if CACHE_REDIS
        , cache
#endif
#if MEDIA_BLOB
        , blobs
#endif
    ).WaitFor(cm);
    var cd2 = builder.AddUmbracoInstance("cd2", "Subscriber2", database, mailpit
#if CACHE_REDIS
        , cache
#endif
#if MEDIA_BLOB
        , blobs
#endif
    ).WaitFor(cd1);
#if REVERSE_PROXY
    builder.AddProject<Projects.Casko_UmbracoTopology_Yarp>("yarp", launchProfileName: "LocalReverseProxy")
        .WithEnvironment(context =>
        {
            context.EnvironmentVariables["ReverseProxy__Clusters__cm__Destinations__default__Address"] = cm.GetEndpoint("https");
            context.EnvironmentVariables["ReverseProxy__Clusters__cd__Destinations__subscriber-1__Address"] = cd1.GetEndpoint("http");
            context.EnvironmentVariables["ReverseProxy__Clusters__cd__Destinations__subscriber-2__Address"] = cd2.GetEndpoint("http");
            foreach (string key in new[] { "ASPNETCORE_Kestrel__Certificates__Default__Path", "ASPNETCORE_Kestrel__Certificates__Default__Password" })
            {
                string? value = Environment.GetEnvironmentVariable(key);
                if (!string.IsNullOrWhiteSpace(value))
                    context.EnvironmentVariables[key] = value;
            }
        })
        .WithReference(cm).WithReference(cd1).WithReference(cd2)
        .WaitFor(cm).WaitFor(cd1).WaitFor(cd2)
        .WithHttpHealthCheck("/alive");
#endif
}
else
{
    throw new InvalidOperationException("TopologyMode must be Cluster or Single");
}

builder.Build().Run();

internal static class UmbracoResources
{
    public static IResourceBuilder<SqlServerDatabaseResource> AddUmbracoDatabase(this IDistributedApplicationBuilder builder)
    {
        string credentials = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,
            "..", "..", "..", "..", ".local", "credentials.env"));
        if (!File.Exists(credentials))
            throw new InvalidOperationException("Missing .local/credentials.env; run scripts/validate-generated.py");
        string[] passwords = File.ReadAllLines(credentials)
            .Where(line => line.StartsWith("SQL_PASSWORD=", StringComparison.Ordinal))
            .Select(line => line["SQL_PASSWORD=".Length..])
            .ToArray();
        if (passwords.Length != 1 || string.IsNullOrWhiteSpace(passwords[0]))
            throw new InvalidOperationException("Missing or invalid SQL_PASSWORD in .local/credentials.env");
        builder.Configuration["Parameters:sql-password"] = passwords[0];
        var password = builder.AddParameter("sql-password", secret: true);
        var sql = builder.AddSqlServer("sql", password)
            .WithImageTag("2022-latest")
            .WithDataVolume("__PROJECT_SLUG__-sql")
            .WithLifetime(ContainerLifetime.Persistent);
        if (builder.ExecutionContext.IsRunMode)
            sql.WithDbGate();
        return sql.AddDatabase("umbracoDbDSN", "Casko.UmbracoTopology");
    }

#if CACHE_REDIS
    public static IResourceBuilder<RedisResource> AddSharedCache(this IDistributedApplicationBuilder builder)
    {
        var cache = builder.AddRedis("cache");
        if (builder.ExecutionContext.IsRunMode)
            cache.WithRedisInsight();
        return cache;
    }
#endif

#if MEDIA_BLOB
    public static IResourceBuilder<AzureBlobStorageResource> AddSharedMediaStore(this IDistributedApplicationBuilder builder)
    {
        var storage = builder.AddAzureStorage("storage")
            .RunAsEmulator(emulator => emulator.WithDataVolume("__PROJECT_SLUG__-azurite"));
        return storage.AddBlobs("blobs");
    }
#endif

    public static IResourceBuilder<ProjectResource> AddUmbracoInstance(
        this IDistributedApplicationBuilder builder,
        string name,
        string profile,
        IResourceBuilder<SqlServerDatabaseResource> database,
        IResourceBuilder<MailPitContainerResource> mailpit
#if CACHE_REDIS
        , IResourceBuilder<RedisResource> cache
#endif
#if MEDIA_BLOB
        , IResourceBuilder<AzureBlobStorageResource> blobs
#endif
    )
    {
        PrepareProfilePaths(profile);
        var project = builder.AddProject<Projects.Casko_UmbracoTopology_Web>(name, launchProfileName: profile)
            .WithReference(database)
            .WaitFor(database)
            .WithReference(mailpit)
            .WaitFor(mailpit)
            .WithEnvironment("Umbraco__CMS__Global__Smtp__Host", mailpit.Resource.Host)
            .WithEnvironment("Umbraco__CMS__Global__Smtp__Port", mailpit.Resource.Port)
            .WithHttpHealthCheck("/health/role");
#if CACHE_REDIS
        project.WithReference(cache).WaitFor(cache);
#endif
#if MEDIA_BLOB
        project.WithReference(blobs).WaitFor(blobs);
#endif
        return project;
    }

    private static void PrepareProfilePaths(string profile)
    {
        string webRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "Casko.UmbracoTopology.Web"));
        string settings = Path.Combine(webRoot, "Properties", "launchSettings.json");
        using JsonDocument json = JsonDocument.Parse(File.ReadAllText(settings));
        var variables = json.RootElement.GetProperty("profiles").GetProperty(profile).GetProperty("environmentVariables");
        foreach (string name in new[] { "TEMP", "TMP", "TMPDIR" })
        {
            string configured = variables.GetProperty(name).GetString()!;
            Directory.CreateDirectory(Path.GetFullPath(configured, webRoot));
            Directory.CreateDirectory(Path.GetFullPath(configured, Directory.GetCurrentDirectory()));
        }
    }
}
