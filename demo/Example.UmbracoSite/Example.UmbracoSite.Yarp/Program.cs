var builder = WebApplication.CreateBuilder(args);
builder.AddServiceDefaults();

string cmDomain = builder.Configuration["ProxyDomains:Cm"] ?? "";
string cdDomain = builder.Configuration["ProxyDomains:Cd"] ?? "";
bool customDomain = !string.Equals(cmDomain, "cm.dev.localhost", StringComparison.OrdinalIgnoreCase) ||
    !string.Equals(cdDomain, "cd.dev.localhost", StringComparison.OrdinalIgnoreCase);
if (customDomain)
{
    string? certificate = builder.Configuration["Kestrel:Certificates:Default:Path"];
    if (string.IsNullOrWhiteSpace(certificate) || !File.Exists(certificate))
        throw new InvalidOperationException("Custom proxy domains require ASPNETCORE_Kestrel__Certificates__Default__Path and Password");
    if (string.IsNullOrWhiteSpace(builder.Configuration["Kestrel:Certificates:Default:Password"]))
        throw new InvalidOperationException("Custom proxy domains require a certificate password");
}

builder.Services.AddReverseProxy().LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));
var app = builder.Build();
app.MapDefaultEndpoints();
app.MapReverseProxy();
app.Run();
