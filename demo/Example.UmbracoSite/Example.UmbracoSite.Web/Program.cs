using System.Globalization;
using System.Net;
using System.Security.Cryptography;
using Casko.SyncExtensionsForUmbraco.Configuration;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Data.SqlClient;
using Umbraco.Cms.Core.HealthChecks;
using Umbraco.Cms.Core.Sync;

WebApplicationBuilder builder = WebApplication.CreateBuilder(args);
builder.AddServiceDefaults();

if (builder.Environment.IsDevelopment())
    builder.Configuration.AddJsonFile("appsettings.Local.json", optional: true, reloadOnChange: true);

bool localTopology = builder.Environment.IsDevelopment()
    && string.Equals(builder.Configuration["UMBRACO_LOCAL_TOPOLOGY"], "true", StringComparison.OrdinalIgnoreCase);
if (localTopology)
{
    CultureInfo culture = CultureInfo.GetCultureInfo("en-US");
    CultureInfo.CurrentCulture = culture;
    CultureInfo.CurrentUICulture = culture;
    CultureInfo.DefaultThreadCurrentCulture = culture;
    CultureInfo.DefaultThreadCurrentUICulture = culture;
}
string role = builder.Configuration["UMBRACO_SERVER_ROLE"] ?? "Single";
bool behindLocalProxy = localTopology && string.Equals(
    builder.Configuration["UMBRACO_LOCAL_REVERSE_PROXY"], "true", StringComparison.OrdinalIgnoreCase);
if (behindLocalProxy)
{
    builder.Services.Configure<ForwardedHeadersOptions>(options =>
    {
        options.ForwardedHeaders = ForwardedHeaders.XForwardedFor |
            ForwardedHeaders.XForwardedHost | ForwardedHeaders.XForwardedProto;
        options.KnownProxies.Add(IPAddress.Loopback);
        options.KnownProxies.Add(IPAddress.IPv6Loopback);
    });
}
if (role is not ("Single" or "SchedulingPublisher" or "Subscriber"))
    throw new InvalidOperationException($"Unknown Umbraco server role: {role}");

if (localTopology)
{
    if (role is "Single" or "SchedulingPublisher")
    {
        string credentials = Path.GetFullPath(Path.Combine(builder.Environment.ContentRootPath, "..", ".local", "credentials.env"));
        builder.Configuration["Umbraco:CMS:Unattended:UnattendedUserEmail"] = ReadCredential(credentials, "ADMIN_EMAIL");
        builder.Configuration["Umbraco:CMS:Unattended:UnattendedUserPassword"] = ReadCredential(credentials, "ADMIN_PASSWORD");
        string apiEmail = ReadCredential(credentials, "API_USER_EMAIL");
        builder.Configuration["uSync:Command:Username"] = apiEmail;
        builder.Configuration["uSync:Command:Email"] = apiEmail;
        string clientId = ReadCredential(credentials, "API_CLIENT_ID");
        if (!clientId.StartsWith("umbraco-back-office-", StringComparison.Ordinal) ||
            clientId.Length == "umbraco-back-office-".Length)
            throw new InvalidOperationException("API_CLIENT_ID must start with umbraco-back-office- and have a suffix");
        builder.Configuration["uSync:Command:ClientId"] = clientId;
        builder.Configuration["uSync:Command:Secret"] = ReadCredential(credentials, "API_CLIENT_SECRET");
    }

    string localRoot = Path.Combine(builder.Environment.ContentRootPath, ".local", "umbraco");
    Directory.CreateDirectory(localRoot);
    foreach (string variable in new[] { "TEMP", "TMP", "TMPDIR" })
    {
        string? configured = builder.Configuration[variable];
        if (string.IsNullOrWhiteSpace(configured))
            throw new InvalidOperationException($"Missing {variable} for local topology");
        string path = Path.GetFullPath(configured, builder.Environment.ContentRootPath);
        Directory.CreateDirectory(path);
        Environment.SetEnvironmentVariable(variable, path);
    }

    string? configuredLog = builder.Configuration["Umbraco:CMS:Logging:Directory"];
    if (string.IsNullOrWhiteSpace(configuredLog))
        throw new InvalidOperationException("Missing local Umbraco log directory");
    string logPath = Path.GetFullPath(configuredLog, builder.Environment.ContentRootPath);
    Directory.CreateDirectory(logPath);
    builder.Configuration["Umbraco:CMS:Logging:Directory"] = logPath;

    string keyRoot = Path.Combine(localRoot, "keys");
    Directory.CreateDirectory(keyRoot);
    builder.Services.AddDataProtection()
        .SetApplicationName("Example.UmbracoSite")
        .PersistKeysToFileSystem(new DirectoryInfo(keyRoot));

    string hmacFile = Path.Combine(localRoot, "imaging-hmac-key");
    if (!File.Exists(hmacFile))
    {
        try
        {
            using FileStream stream = new(hmacFile, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            using StreamWriter writer = new(stream);
            writer.Write(Convert.ToBase64String(RandomNumberGenerator.GetBytes(64)));
        }
        catch (IOException) when (File.Exists(hmacFile)) { }
    }
    builder.Configuration["Umbraco:CMS:Imaging:HMACSecretKey"] = File.ReadAllText(hmacFile);

    string databaseConnection = builder.Configuration.GetConnectionString("umbracoDbDSN")
        ?? throw new InvalidOperationException("Missing Aspire SQL connection string for distributed cache");
    await EnsureSqlCacheTableAsync(databaseConnection);
    builder.Services.AddDistributedSqlServerCache(options =>
    {
        options.ConnectionString = databaseConnection;
        options.SchemaName = "dbo";
        options.TableName = "DistributedCache";
    });

    string configuredMediaRoot = builder.Configuration["Umbraco:CMS:Global:UmbracoMediaPhysicalRootPath"]
        ?? throw new InvalidOperationException("Missing shared filesystem media root");
    string mediaRoot = Path.GetFullPath(configuredMediaRoot, builder.Environment.ContentRootPath);
    Directory.CreateDirectory(mediaRoot);
    builder.Configuration["Umbraco:CMS:Global:UmbracoMediaPhysicalRootPath"] = mediaRoot;
}

var umbraco = builder.CreateUmbracoBuilder()
    .AddServerRole(role)
    .AddBackOffice()
    .AddWebsite()
    .AddComposers();
umbraco.Build();

WebApplication app = builder.Build();
if (behindLocalProxy)
    app.UseForwardedHeaders();
app.MapDefaultEndpoints();
await app.BootUmbracoAsync();

if (localTopology && role is ("Single" or "SchedulingPublisher") &&
    builder.Configuration.GetValue<bool>("Umbraco:CMS:HealthChecks:Notification:Enabled"))
{
    app.Lifetime.ApplicationStarted.Register(() => _ = Task.Run(async () =>
    {
        try
        {
            using IServiceScope scope = app.Services.CreateScope();
            var checks = scope.ServiceProvider.GetRequiredService<HealthCheckCollection>();
            var methods = scope.ServiceProvider.GetRequiredService<HealthCheckNotificationMethodCollection>();
            HealthCheckResults results = await HealthCheckResults.Create(checks);
            foreach (var method in methods.Where(method => method.Enabled))
                await method.SendAsync(results);
        }
        catch (Exception exception)
        {
            app.Logger.LogError(exception, "Startup health check notification failed");
        }
    }));
}

if (localTopology)
{
    app.MapGet("/health/role", (IServerRoleAccessor accessor) =>
        Results.Ok(new { role = accessor.CurrentServerRole.ToString() }));
}

if (localTopology && role == "Subscriber")
{
    app.Use(async (context, next) =>
    {
        if (context.Request.Path.StartsWithSegments("/umbraco", StringComparison.OrdinalIgnoreCase))
        {
            context.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        await next();
    });
}

app.UseUmbraco()
    .WithMiddleware(u =>
    {
        u.UseBackOffice();
        u.UseWebsite();
    })
    .WithEndpoints(u =>
    {
        u.UseBackOfficeEndpoints();
        u.UseWebsiteEndpoints();
    });

await app.RunAsync();

static string ReadCredential(string path, string key)
{
    string prefix = key + "=";
    string[] values = File.ReadAllLines(path)
        .Where(line => line.StartsWith(prefix, StringComparison.Ordinal))
        .Select(line => line[prefix.Length..])
        .ToArray();
    if (values.Length != 1 || string.IsNullOrWhiteSpace(values[0]))
        throw new InvalidOperationException($"Missing or invalid {key} in {path}");
    return values[0];
}

static async Task EnsureSqlCacheTableAsync(string connectionString)
{
    await using var connection = new SqlConnection(connectionString);
    await connection.OpenAsync();
    await using var command = connection.CreateCommand();
    command.CommandText = """
        IF OBJECT_ID(N'dbo.DistributedCache', N'U') IS NULL
        BEGIN
            CREATE TABLE [dbo].[DistributedCache] (
                [Id] nvarchar(449) COLLATE SQL_Latin1_General_CP1_CS_AS NOT NULL,
                [Value] varbinary(max) NOT NULL,
                [ExpiresAtTime] datetimeoffset(7) NOT NULL,
                [SlidingExpirationInSeconds] bigint NULL,
                [AbsoluteExpiration] datetimeoffset(7) NULL,
                CONSTRAINT [PK_DistributedCache] PRIMARY KEY CLUSTERED ([Id] ASC)
            );
            CREATE NONCLUSTERED INDEX [IX_DistributedCache_ExpiresAtTime]
                ON [dbo].[DistributedCache] ([ExpiresAtTime] ASC);
        END
        """;
    await command.ExecuteNonQueryAsync();
}
