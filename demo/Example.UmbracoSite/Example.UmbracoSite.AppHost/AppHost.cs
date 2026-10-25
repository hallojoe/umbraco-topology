using System.Text.Json;
using Aspire.Hosting.ApplicationModel;
using Aspire.Hosting.JavaScript;

var builder = DistributedApplication.CreateBuilder(args);

var database = builder.AddUmbracoDatabase();
var mailpit = builder.AddMailPit("mailpit");
builder.AddDemoFrontend();

string mode = builder.Configuration["TopologyMode"] ?? "Cluster";
if (mode == "Single")
{
    builder.AddUmbracoInstance("single", "Single", database, mailpit
    );
}
else if (mode == "Cluster")
{
    var cm = builder.AddUmbracoInstance("cm", "SchedulingPublisher", database, mailpit
    );
    var cd1 = builder.AddUmbracoInstance("cd1", "Subscriber1", database, mailpit
    ).WaitFor(cm);
    var cd2 = builder.AddUmbracoInstance("cd2", "Subscriber2", database, mailpit
    ).WaitFor(cd1);
    builder.AddProject<Projects.Example_UmbracoSite_Yarp>("yarp", launchProfileName: "LocalReverseProxy")
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
}
else
{
    throw new InvalidOperationException("TopologyMode must be Cluster or Single");
}

builder.Build().Run();

internal static class FrontendResources
{
    public static IResourceBuilder<ViteAppResource> AddDemoFrontend(this IDistributedApplicationBuilder builder)
    {
#pragma warning disable ASPIREJAVASCRIPT001
        return builder.AddViteApp("frontend", "../frontend")
            .PublishAsStaticWebsite()
            .WithExternalHttpEndpoints();
#pragma warning restore ASPIREJAVASCRIPT001
    }
}

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
            .WithDataVolume("example-umbracosite-sql")
            .WithLifetime(ContainerLifetime.Persistent);
        if (builder.ExecutionContext.IsRunMode)
            sql.WithDbGate();
        return sql.AddDatabase("umbracoDbDSN", "Example.UmbracoSite");
    }



    public static IResourceBuilder<ProjectResource> AddUmbracoInstance(
        this IDistributedApplicationBuilder builder,
        string name,
        string profile,
        IResourceBuilder<SqlServerDatabaseResource> database,
        IResourceBuilder<MailPitContainerResource> mailpit
    )
    {
        PrepareProfilePaths(profile);
        var project = builder.AddProject<Projects.Example_UmbracoSite_Web>(name, launchProfileName: profile)
            .WithReference(database)
            .WaitFor(database)
            .WithReference(mailpit)
            .WaitFor(mailpit)
            .WithEnvironment("Umbraco__CMS__Global__Smtp__Host", mailpit.Resource.Host)
            .WithEnvironment("Umbraco__CMS__Global__Smtp__Port", mailpit.Resource.Port)
            .WithHttpHealthCheck("/health/role");
        return project;
    }

    private static void PrepareProfilePaths(string profile)
    {
        string webRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "Example.UmbracoSite.Web"));
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
