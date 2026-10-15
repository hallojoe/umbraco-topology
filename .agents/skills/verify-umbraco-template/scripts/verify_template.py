#!/usr/bin/env python3
"""Generate, inspect, build, and optionally boot every provider combination."""
import argparse
import base64
import hashlib
import hmac
import itertools
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.parse
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET

TEMPLATE = Path(__file__).resolve().parents[4] / "src" / "UmbracoTopology.Template"
SECRET_VALUES = ["VerifyAdmin!234", "VerifyApi!567", "VerifySql!890"]


def run(args, *, cwd=None, timeout=300, env=None):
    if args[:3] == ["dotnet", "new", "casko-umbraco-topology"]:
        args = [*args, "--allow-scripts", "Yes"]
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout, env=env)
    if result.returncode:
        output = (result.stdout + result.stderr)[-5000:]
        for secret in SECRET_VALUES:
            output = output.replace(secret, "[redacted]")
        raise RuntimeError(f"Command failed ({args[0]}):\n{output}")
    return result.stdout


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def profile_urls(web):
    profiles = json.loads((web / "Properties/launchSettings.json").read_text())["profiles"]
    return {key: value["applicationUrl"].split(";")[0] for key, value in profiles.items()}


def inspect(root, name, cache, media, custom, proxy):
    web = root / f"{name}.Web"
    host = root / f"{name}.AppHost"
    require((root / f"{name}.slnx").is_file(), "solution name was not replaced")
    require((web / "uSync/v17").is_dir(), "sample uSync snapshot is missing")
    require("83c2573e-b263-416a-ac2a-fc4d4d142f91" not in
            (host / f"{name}.AppHost.csproj").read_text(), "user-secrets ID was not regenerated")
    require("6fc1480e-e27f-4409-88ad-35d519332731" not in
            (web / "appsettings.json").read_text(), "Umbraco Global ID was not regenerated")
    require("32a9a9ac-7f72-4d8f-ad5b-ee9f771b5e1f" in
            (web / "uSync/v17/Content/home.config").read_text(), "sample content ID changed")
    ignored = (root / ".gitignore").read_text()
    require(".local/" in ignored, "credentials are not ignored")
    require(".codex/config.toml" in ignored, "Codex MCP credentials are not ignored")
    credentials = root / ".local/credentials.env"
    require(credentials.is_file(), "credential file is missing")
    values = dict(line.split("=", 1) for line in credentials.read_text().splitlines())
    expected = {
        "ADMIN_EMAIL": "verify-admin@example.com" if custom else "admin@cm.dev.localhost",
        "ADMIN_PASSWORD": SECRET_VALUES[0] if custom else "1234567890",
        "SQL_PASSWORD": SECRET_VALUES[2] if custom else "LocalSql!1234567890",
        "API_USER_EMAIL": "verify-api@dev.localhost" if custom else "apiuser@dev.localhost",
        "API_CLIENT_ID": "umbraco-back-office-verification" if custom else "umbraco-back-office-api-user",
        "API_CLIENT_SECRET": SECRET_VALUES[1] if custom else "1234567890",
    }
    require(values == expected, "generated credentials differ from selected values")
    tracked_candidates = [root / f"{name}.slnx", web / "Program.cs", web / "Properties/launchSettings.json",
                          host / "AppHost.cs", root / "README.md"]
    for candidate in tracked_candidates:
        contents = candidate.read_text()
        require(all(value not in contents for value in SECRET_VALUES), f"secret found in {candidate.name}")
        require("Casko.UmbracoTopology" not in contents, f"fixture name remains in {candidate.name}")
    for candidate in root.rglob("*"):
        if not candidate.is_file() or any(part in {".local", "bin", "obj", "node_modules"}
                                          for part in candidate.relative_to(root).parts):
            continue
        try:
            contents = candidate.read_text()
        except UnicodeDecodeError:
            continue
        require(all(value not in contents for value in SECRET_VALUES),
                f"custom secret found in generated source: {candidate.relative_to(root)}")

    program = (web / "Program.cs").read_text()
    apphost = (host / "AppHost.cs").read_text()
    web_project = ET.parse(web / f"{name}.Web.csproj")
    packages = {entry.attrib["Include"]: entry.attrib.get("Condition", "")
                for entry in web_project.iter("PackageReference")}
    require(("AddRedisDistributedCache" in program) == (cache == "redis"), "cache code mismatch")
    require(("EnsureSqlCacheTableAsync" in program) == (cache == "mssql"), "SQL cache code mismatch")
    require(("AddAzureBlobMediaFileSystem" in program) == (media == "blob"), "media code mismatch")
    require(("AddSharedCache" in apphost) == (cache == "redis"), "Redis resource mismatch")
    require(("AddSharedMediaStore" in apphost) == (media == "blob"), "Blob resource mismatch")
    require("AddMailPit" in apphost and "AddServiceDefaults" in program,
            "Mailpit or Service Defaults is missing")
    defaults = (root / f"{name}.ServiceDefaults/Extensions.cs").read_text()
    require("WithMetrics" in defaults and "WithTracing" in defaults and "UseOtlpExporter" in defaults,
            "Service Defaults telemetry is incomplete")
    require((root / f"{name}.Yarp").is_dir() == proxy, "YARP project selection mismatch")
    require((".Yarp/" in (root / f"{name}.slnx").read_text()) == proxy,
            "YARP solution entry mismatch")
    require("'redis'" in packages["Aspire.StackExchange.Redis.DistributedCaching"], "Redis package condition missing")
    require("'mssql'" in packages["Microsoft.Extensions.Caching.SqlServer"], "SQL cache package condition missing")
    require("'blob'" in packages["Umbraco.StorageProviders.AzureBlob"], "Blob package condition missing")

    profiles = json.loads((web / "Properties/launchSettings.json").read_text())["profiles"]
    require(set(profiles) == {"Single", "SchedulingPublisher", "Subscriber1", "Subscriber2"}, "role profiles missing")
    for role, profile in profiles.items():
        env = profile["environmentVariables"]
        require(("Umbraco__CMS__Global__UmbracoMediaPhysicalRootPath" in env) == (media == "filesystem"),
                "media launch setting mismatch")
        require("UMBRACO_LOCAL_TOPOLOGY" in env, "local topology setting missing")
        require(not any("Password" in key or "Secret" in key for key in env), "secret in launch settings")
        require(env["Umbraco__CMS__Global__Smtp__From"] == "notifications@cm.dev.localhost",
                "SMTP sender mismatch")
        require(env["Umbraco__CMS__Global__Smtp__Host"] == "localhost" and
                env["Umbraco__CMS__Global__Smtp__Port"] == "1025", "SMTP launch fallback mismatch")
        require(env["Umbraco__CMS__Content__Notifications__Email"] == "notifications@cm.dev.localhost",
                "notification sender mismatch")
        require(("Umbraco__CMS__HealthChecks__Notification__Enabled" in env) ==
                (role in ("Single", "SchedulingPublisher")), "health notification role mismatch")
        if role in ("Single", "SchedulingPublisher"):
            require(env["Umbraco__CMS__HealthChecks__Notification__Period"] == "1.00:00:00" and
                    env["Umbraco__CMS__HealthChecks__Notification__FirstRunTime"] == "0 4 * * *",
                    "daily health schedule mismatch")
            require(env["Umbraco__CMS__HealthChecks__Notification__NotificationMethods__email__Settings__RecipientEmail"] ==
                    values["ADMIN_EMAIL"], "health notification recipient mismatch")
    ports = [int(port) for profile in profiles.values() for port in
             re.findall(r"localhost:(\d+)", profile["applicationUrl"])]
    require(len(ports) == 8 and len(set(ports)) == 8, "web ports are not distinct")
    app_profile = json.loads((host / "Properties/launchSettings.json").read_text())["profiles"]["Development"]
    app_ports = [int(port) for port in re.findall(r"localhost:(\d+)",
                 app_profile["applicationUrl"] + json.dumps(app_profile["environmentVariables"]))]
    require(len(app_ports) == 4 and len(set(ports + app_ports)) == 12, "AppHost ports are not distinct")
    require(ports[6] == ports[4] + 1, "CD2 HTTPS port is not adjacent to CD1")
    require(("UMBRACO_LOCAL_REVERSE_PROXY" in profiles["SchedulingPublisher"]["environmentVariables"]) == proxy,
            "proxy setting mismatch")
    if proxy:
        require(profiles["SchedulingPublisher"]["environmentVariables"]["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"] ==
                "https://cm.dev.localhost:4443/", "CM public URL mismatch")
        require(profiles["Subscriber1"]["environmentVariables"]["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"] ==
                "https://cd.dev.localhost:4443/", "CD public URL mismatch")
        yarp = json.loads((root / f"{name}.Yarp/appsettings.Development.json").read_text())
        require(yarp["ReverseProxy"]["Clusters"]["cm"]["Destinations"]["default"]["Address"] ==
                f"https://localhost:{ports[2]}/", "YARP CM fallback does not match the private port")
    readme = (root / "README.md").read_text()
    require(not re.search(r"__[A-Z0-9_]+__", readme),
            "README URL placeholders remain")
    return web, host


def inspect_restore(web, cache, media):
    assets = json.loads((web / "obj/project.assets.json").read_text())
    libraries = set(assets["libraries"])
    has_package = lambda package: any(item.startswith(package + "/") for item in libraries)
    require(has_package("Microsoft.Extensions.Caching.SqlServer") == (cache == "mssql"),
            "restored SQL cache package mismatch")
    require(has_package("Aspire.StackExchange.Redis.DistributedCaching") == (cache == "redis"),
            "restored Redis cache package mismatch")
    require(has_package("Umbraco.StorageProviders.AzureBlob") == (media == "blob"),
            "restored Blob package mismatch")


def fetch(url):
    with urllib.request.urlopen(url, context=ssl._create_unverified_context(), timeout=15) as response:
        require(response.status == 200, f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8")


def wait_site(url, profile, marker="Welcome"):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            home = fetch(url + "/")
            about = fetch(url + "/about/")
            if marker in home and "About" in home and "About this site" in about:
                return
        except (OSError, AssertionError):
            pass
        time.sleep(2)
    raise AssertionError(f"published sample site did not reach {profile} within 90 seconds")


def api_headers(root, cm_url):
    values = dict(line.split("=", 1) for line in (root / ".local/credentials.env").read_text().splitlines())
    token_data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": values["API_CLIENT_ID"],
        "client_secret": values["API_CLIENT_SECRET"],
    }).encode()
    token_request = urllib.request.Request(
        cm_url + "/umbraco/management/api/v1/security/back-office/token", data=token_data)
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(token_request, context=context, timeout=15) as response:
        token = json.load(response)["access_token"]
    return {"Authorization": "Bearer " + token, "Content-Type": "application/json"}, context


def publish_change(root, cm_url):
    headers, context = api_headers(root, cm_url)
    document_url = cm_url + "/umbraco/management/api/v1/document/32a9a9ac-7f72-4d8f-ad5b-ee9f771b5e1f"
    with urllib.request.urlopen(urllib.request.Request(document_url, headers=headers), context=context,
                                timeout=15) as response:
        document = json.load(response)
    marker = "Welcome runtime " + secrets.token_hex(4)
    properties = [{"alias": item["alias"], "value": marker if item["alias"] == "title" else item["value"]}
                  for item in document["values"]]
    require(any(item["alias"] == "title" for item in properties), "sample Home title is missing")
    payload = {"values": properties, "variants": [{"name": item["name"], "culture": item["culture"]}
                                                   for item in document["variants"]],
               "template": document["template"]}
    for suffix, body in (("", payload), ("/publish", {"publishSchedules": [{"culture": None}]})):
        request = urllib.request.Request(document_url + suffix, data=json.dumps(body).encode(),
                                         method="PUT", headers=headers)
        with urllib.request.urlopen(request, context=context, timeout=20) as response:
            require(response.status == 200, "document update or publish failed")
    return marker


def upload_media(root, cm_url):
    headers, context = api_headers(root, cm_url)
    api = cm_url + "/umbraco/management/api/v1"
    with urllib.request.urlopen(urllib.request.Request(api + "/media-type/allowed-at-root", headers=headers),
                                context=context, timeout=15) as response:
        types = json.load(response)
    file_type = next(item["id"] for item in types["items"] if item["name"] == "File")
    file_id, media_id = str(uuid.uuid4()), str(uuid.uuid4())
    boundary = "----template" + secrets.token_hex(12)
    contents = b"template media verification\n"
    form = (f'--{boundary}\r\nContent-Disposition: form-data; name="Id"\r\n\r\n{file_id}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="File"; filename="verification.txt"\r\n'
            f'Content-Type: text/plain\r\n\r\n').encode() + contents + f'\r\n--{boundary}--\r\n'.encode()
    upload = urllib.request.Request(api + "/temporary-file", data=form,
                                    headers={"Authorization": headers["Authorization"],
                                             "Content-Type": "multipart/form-data; boundary=" + boundary})
    with urllib.request.urlopen(upload, context=context, timeout=20) as response:
        require(response.status == 201, "temporary media upload failed")
    payload = {"id": media_id, "parent": None, "mediaType": {"id": file_type},
               "values": [{"alias": "umbracoFile", "value": {"temporaryFileId": file_id}}],
               "variants": [{"name": "Runtime media"}]}
    create = urllib.request.Request(api + "/media", data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(create, context=context, timeout=20) as response:
        require(response.status == 201, "media creation failed")
    with urllib.request.urlopen(urllib.request.Request(api + "/media/" + media_id, headers=headers),
                                context=context, timeout=15) as response:
        media = json.load(response)
    source = next(item["value"]["src"] for item in media["values"] if item["alias"] == "umbracoFile")
    require(source.startswith("/media/"), "media path was not generated")
    return source, contents


def wait_media(url, path, expected):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + path, context=ssl._create_unverified_context(),
                                        timeout=15) as response:
                if response.status == 200 and response.read() == expected:
                    return
        except OSError:
            pass
        time.sleep(2)
    raise AssertionError(f"uploaded media did not reach {url} within 90 seconds")


def check_subscriber_backoffice(url):
    for path in ("/umbraco", "/umbraco/management/api/v1/server/status"):
        try:
            urllib.request.urlopen(url + path, context=ssl._create_unverified_context(), timeout=15)
        except urllib.error.HTTPError as error:
            require(error.code == 404, f"Subscriber served {path}: HTTP {error.code}")
        else:
            raise AssertionError(f"Subscriber served {path}")


def check_admin_credentials(root, name):
    """Verify the installed user's password hash against the template option."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    containers = run(["podman", "ps", "-q", "--filter", f"volume={slug}-sql"]).splitlines()
    require(len(containers) == 1, "expected one running SQL container")
    container = containers[0]
    details = json.loads(run(["podman", "inspect", container]))[0]
    sql_passwords = [entry.split("=", 1)[1] for entry in details["Config"]["Env"]
                     if entry.startswith("MSSQL_SA_PASSWORD=")]
    require(len(sql_passwords) == 1, "SQL container has no SA password")
    query = "SET NOCOUNT ON; SELECT userEmail + '|' + userPassword FROM umbracoUser WHERE id = -1"
    output = run(["podman", "exec", "-e", f"SQLCMDPASSWORD={sql_passwords[0]}", container,
                  "/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost", "-U", "sa", "-C",
                  "-d", name, "-Q", query, "-h", "-1", "-W"])
    email, encoded = output.strip().split("|", 1)
    values = dict(line.split("=", 1) for line in (root / ".local/credentials.env").read_text().splitlines())
    require(sql_passwords[0] == values["SQL_PASSWORD"], "SQL container password differs from template option")
    require(email == values["ADMIN_EMAIL"], "installed administrator email differs from template option")
    digest = base64.b64decode(encoded)
    require(digest[0] == 1 and len(digest) >= 14, "unexpected administrator password hash format")
    prf = int.from_bytes(digest[1:5], "big")
    iterations = int.from_bytes(digest[5:9], "big")
    salt_length = int.from_bytes(digest[9:13], "big")
    require(prf in (0, 1, 2) and iterations > 0 and salt_length > 0 and len(digest) > 13 + salt_length,
            "invalid administrator password hash")
    algorithm = {0: "sha1", 1: "sha256", 2: "sha512"}[prf]
    salt = digest[13:13 + salt_length]
    expected = digest[13 + salt_length:]
    actual = hashlib.pbkdf2_hmac(algorithm, values["ADMIN_PASSWORD"].encode(), salt, iterations,
                                 dklen=len(expected))
    require(hmac.compare_digest(actual, expected), "administrator password differs from template option")
    api_query = ("SET NOCOUNT ON; SELECT u.userEmail + '|' + u.userLogin + '|' + c.clientId "
                 "FROM umbracoUser u JOIN umbracoUser2ClientId c ON c.userId = u.id")
    api_users = run(["podman", "exec", "-e", f"SQLCMDPASSWORD={sql_passwords[0]}", container,
                     "/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost", "-U", "sa", "-C",
                     "-d", name, "-Q", api_query, "-h", "-1", "-W"]).splitlines()
    expected_user = "|".join((values["API_USER_EMAIL"], values["API_USER_EMAIL"], values["API_CLIENT_ID"]))
    require(expected_user in api_users, "provisioned API user differs from template options")


def inject_failing_health_check(web):
    (web / "VerificationHealthCheck.cs").write_text('''using Umbraco.Cms.Core.HealthChecks;

[HealthCheck("E6C5E254-D124-40AD-9830-7C3FB13A904A", "Template verification failure",
    Description = "Checks health email delivery in a temporary project.", Group = "Verification")]
public sealed class VerificationHealthCheck : HealthCheck
{
    public override Task<IEnumerable<HealthCheckStatus>> GetStatusAsync() =>
        Task.FromResult<IEnumerable<HealthCheckStatus>>(new[]
        {
            new HealthCheckStatus("Expected verification failure") { ResultType = StatusResultType.Error }
        });

    public override HealthCheckStatus ExecuteAction(HealthCheckAction action) =>
        throw new NotSupportedException();
}
''')


def wait_health_mail(root):
    description = run(["aspire", "describe", "--non-interactive"], cwd=root)
    match = re.search(r"mailpit[^\n]*http://localhost:(\d+)", description)
    require(match is not None, "Mailpit HTTP endpoint is missing")
    url = f"http://localhost:{match.group(1)}/api/v1/messages"
    recipient = dict(line.split("=", 1) for line in (root / ".local/credentials.env").read_text().splitlines())["ADMIN_EMAIL"]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        with urllib.request.urlopen(url, timeout=10) as response:
            messages = json.load(response)["messages"]
        for message in messages:
            if recipient in json.dumps(message):
                require("scheduledHealthCheckEmailSubject" not in message["Subject"],
                        "health email subject was not localized")
                require("scheduledHealthCheckEmailBody" not in message["Snippet"],
                        "health email body was not localized")
                return
        time.sleep(3)
    raise AssertionError("Mailpit did not receive a failed health-check email for the admin")


def check_telemetry(root, resources):
    for resource in resources:
        for _ in range(10):
            spans = run(["aspire", "otel", "spans", resource, "--limit", "50", "--format", "Json",
                         "--non-interactive"], cwd=root, timeout=30)
            if "GET" in spans or "/about" in spans:
                break
            time.sleep(2)
        else:
            raise AssertionError(f"Aspire dashboard has no HTTP spans for {resource}")


def smoke(root, web, host, name, check_mcp, proxy):
    started = False
    try:
        run(["aspire", "start", "--launch-profile", "Development", "--non-interactive"], cwd=root, timeout=180)
        started = True
        for role in (("cm", "cd1", "cd2", "yarp") if proxy else ("cm", "cd1", "cd2")):
            run(["aspire", "wait", role, "--non-interactive"], cwd=root, timeout=180)
        urls = profile_urls(web)
        public = {key: value["environmentVariables"]["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"].rstrip("/")
                  for key, value in json.loads((web / "Properties/launchSettings.json").read_text())["profiles"].items()}
        for profile in ("SchedulingPublisher", "Subscriber1", "Subscriber2"):
            wait_site(urls[profile], profile)
            if proxy:
                wait_site(public[profile], profile + " public")
        for profile in ("SchedulingPublisher", "Subscriber1", "Subscriber2"):
            fetch(urls[profile] + "/alive")
        if proxy:
            fetch(public["SchedulingPublisher"] + "/alive")
            fetch(public["Subscriber1"] + "/alive")
        check_telemetry(root, ("cm", "cd1", "cd2", "yarp") if proxy else ("cm", "cd1", "cd2"))
        wait_health_mail(root)
        check_admin_credentials(root, name)
        for profile in ("Subscriber1", "Subscriber2"):
            check_subscriber_backoffice(urls[profile])
        if proxy:
            check_subscriber_backoffice(public["Subscriber1"])
        marker = publish_change(root, urls["SchedulingPublisher"])
        media_path, media_bytes = upload_media(root, urls["SchedulingPublisher"])
        for profile in ("SchedulingPublisher", "Subscriber1", "Subscriber2"):
            wait_site(urls[profile], profile, marker)
            wait_media(urls[profile], media_path, media_bytes)
            if proxy:
                wait_site(public[profile], profile + " public", marker)
                wait_media(public[profile], media_path, media_bytes)
        if check_mcp:
            run(["npm", "ci", "--prefix", "mcp"], cwd=root, timeout=180)
            run(["python3", "scripts/configure-mcp.py"], cwd=root)
            require((root / ".mcp.json").stat().st_mode & 0o077 == 0,
                    "MCP configuration permissions are too broad")
            codex_path = root / ".codex/config.toml"
            require(codex_path.stat().st_mode & 0o077 == 0,
                    "Codex MCP configuration permissions are too broad")
            server_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            claude_server = json.loads((root / ".mcp.json").read_text())["mcpServers"][server_name]
            codex_server = tomllib.loads(codex_path.read_text())["mcp_servers"][server_name]
            require(codex_server["command"] == claude_server["command"] and
                    codex_server["args"] == claude_server["args"] and
                    codex_server["env"] == claude_server["env"],
                    "Codex and Claude MCP settings differ")
            run(["node", "mcp/check.mjs"], cwd=root, timeout=90)
        run(["aspire", "stop", "--non-interactive"], cwd=root, timeout=90)
        started = False

        single_env = dict(os.environ, TopologyMode="Single")
        run(["aspire", "start", "--launch-profile", "Development", "--non-interactive"],
            cwd=root, timeout=180, env=single_env)
        started = True
        run(["aspire", "wait", "single", "--non-interactive"], cwd=root, timeout=180)
        wait_site(urls["Single"], "Single", marker)
        wait_media(urls["Single"], media_path, media_bytes)
        for log in (web / ".local/umbraco/logs").glob("*.json"):
            require(all(value not in log.read_text() for value in SECRET_VALUES),
                    f"custom secret found in {log.name}")
    finally:
        if started:
            subprocess.run(["aspire", "stop", "--non-interactive"], cwd=root,
                           text=True, capture_output=True, timeout=90)
        cleanup_volumes(name, "podman")


def cleanup_volumes(name, runtime):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    for volume in (f"{slug}-sql", f"{slug}-sql-secrets", f"{slug}-azurite"):
        containers = subprocess.run([runtime, "ps", "-aq", "--filter", f"volume={volume}"],
                                    text=True, capture_output=True, check=True).stdout.splitlines()
        if containers:
            run([runtime, "rm", "-f", *containers], timeout=60)
        subprocess.run([runtime, "volume", "rm", volume], text=True, capture_output=True)


def single_smoke(root, web, name, runtime):
    start_attempted = False
    try:
        single_env = dict(os.environ, TopologyMode="Single")
        start_attempted = True
        run(["aspire", "start", "--launch-profile", "Development", "--no-build", "--non-interactive"],
            cwd=root, timeout=180, env=single_env)
        for resource in ("mailpit", "single"):
            run(["aspire", "wait", resource, "--non-interactive"], cwd=root, timeout=180)
        url = profile_urls(web)["Single"]
        wait_site(url, "Single")
        require("Single" in fetch(url + "/health/role"), "Single role endpoint mismatch")
        marker = publish_change(root, url)
        wait_site(url, "Single", marker)
        media_path, media_bytes = upload_media(root, url)
        wait_media(url, media_path, media_bytes)
        check_telemetry(root, ("single",))
        wait_health_mail(root)
        run(["npm", "ci", "--prefix", "mcp"], cwd=root, timeout=180)
        run(["python3", "scripts/configure-mcp.py"], cwd=root,
            env=dict(os.environ, UMBRACO_BASE_URL=url))
        run(["node", "mcp/check.mjs"], cwd=root, timeout=90)
    except Exception:
        if start_attempted:
            for command in (("aspire", "describe", "--non-interactive"),
                            ("aspire", "logs", "single", "--tail", "100", "--non-interactive")):
                result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=30)
                print((result.stdout + result.stderr)[-8000:], file=sys.stderr)
        raise
    finally:
        if start_attempted:
            subprocess.run(["aspire", "stop", "--non-interactive"], cwd=root,
                           text=True, capture_output=True, timeout=90)
        cleanup_volumes(name, runtime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--runtime", action="store_true", help="boot each generated topology and check content and media with Podman")
    modes.add_argument("--single-smoke", action="store_true", help="boot one default Single topology with Docker")
    parser.add_argument("--smoke-container-runtime", choices=("docker", "podman"), default="docker",
                        help="container runtime for --single-smoke (default: docker)")
    parser.add_argument("--pair", choices=("redis+blob", "redis+filesystem", "mssql+blob", "mssql+filesystem"),
                        help="check only one provider combination")
    args = parser.parse_args()
    if args.single_smoke and args.pair:
        parser.error("--pair cannot be used with --single-smoke")
    with tempfile.TemporaryDirectory(prefix="umbraco-template-check-") as temporary:
        base = Path(temporary)
        hive = base / "hive"
        run(["dotnet", "new", "install", str(TEMPLATE), "--debug:custom-hive", str(hive)])
        if args.single_smoke:
            name = "Verify.Single.V" + secrets.token_hex(3)
            root = base / "single-smoke"
            run(["dotnet", "new", "casko-umbraco-topology", "--name", name,
                 "--output", str(root), "--container-runtime", args.smoke_container_runtime,
                 "--debug:custom-hive", str(hive)])
            web, _ = inspect(root, name, "redis", "blob", False, False)
            run(["python3", "scripts/validate-generated.py"], cwd=root)
            inject_failing_health_check(web)
            run(["dotnet", "build", str(root / f"{name}.slnx"), "-v:q", "-clp:ErrorsOnly"],
                timeout=600)
            inspect_restore(web, "redis", "blob")
            single_smoke(root, web, name, args.smoke_container_runtime)
            print("PASS redis+blob+direct: generated, inspected, built, booted in Single mode")
            return
        for option in ("admin-email", "admin-password", "sql-password", "api-user-email", "api-client-id", "api-client-secret"):
            rejected = subprocess.run(["dotnet", "new", "casko-umbraco-topology", "--name", "Invalid.Empty",
                                       "--output", str(base / f"invalid-{option}"), f"--{option}", "",
                                       "--debug:custom-hive", str(hive)], text=True, capture_output=True)
            require(rejected.returncode == 102, f"empty {option} was not rejected during generation")
        invalid_id = base / "invalid-prefix"
        run(["dotnet", "new", "casko-umbraco-topology", "--name", "Invalid.Prefix",
             "--output", str(invalid_id), "--api-client-id", "back-office-api-user",
             "--debug:custom-hive", str(hive)])
        rejected = subprocess.run(["python3", "scripts/validate-generated.py"], cwd=invalid_id,
                                  text=True, capture_output=True)
        require(rejected.returncode != 0, "API client ID without the Umbraco prefix was accepted")
        invalid_sql = base / "invalid-sql"
        run(["dotnet", "new", "casko-umbraco-topology", "--name", "Invalid.Sql",
             "--output", str(invalid_sql), "--sql-password", "12345678",
             "--debug:custom-hive", str(hive)])
        rejected = subprocess.run(["python3", "scripts/validate-generated.py"], cwd=invalid_sql,
                                  text=True, capture_output=True)
        require(rejected.returncode != 0, "weak SQL password was accepted")
        custom_root = base / "custom-network"
        run(["dotnet", "new", "casko-umbraco-topology", "--name", "Verify.CustomNetwork",
             "--output", str(custom_root), "--reverse-proxy", "--cm-port", "64222",
             "--cd-port", "44222", "--proxy-port", "4443", "--cm-domain", "editor.dev.localhost",
             "--cd-domain", "reader.dev.localhost", "--debug:custom-hive", str(hive)])
        custom_profiles = json.loads((custom_root / "Verify.CustomNetwork.Web/Properties/launchSettings.json").read_text())["profiles"]
        require(profile_urls(custom_root / "Verify.CustomNetwork.Web")["SchedulingPublisher"] ==
                "https://localhost:64222", "custom CM private port mismatch")
        require(profile_urls(custom_root / "Verify.CustomNetwork.Web")["Subscriber2"] ==
                "https://localhost:44223", "custom CD2 private port mismatch")
        require(custom_profiles["SchedulingPublisher"]["environmentVariables"]
                ["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"] ==
                "https://editor.dev.localhost:4443/", "custom CM public URL mismatch")
        require(custom_profiles["Subscriber1"]["environmentVariables"]
                ["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"] ==
                "https://reader.dev.localhost:4443/", "custom CD public URL mismatch")
        require(custom_profiles["SchedulingPublisher"]["environmentVariables"]
                ["Umbraco__CMS__Global__Smtp__From"] == "notifications@editor.dev.localhost",
                "custom SMTP sender mismatch")
        custom_yarp = json.loads((custom_root / "Verify.CustomNetwork.Yarp/appsettings.Development.json").read_text())
        require(custom_yarp["ReverseProxy"]["Clusters"]["cm"]["Destinations"]["default"]["Address"] ==
                "https://localhost:64222/", "custom YARP CM fallback mismatch")
        run(["dotnet", "build", "Verify.CustomNetwork.slnx", "-v:q", "-clp:ErrorsOnly"], cwd=custom_root)
        no_certificate = dict(os.environ)
        no_certificate.pop("ASPNETCORE_Kestrel__Certificates__Default__Path", None)
        no_certificate.pop("ASPNETCORE_Kestrel__Certificates__Default__Password", None)
        missing_certificate = subprocess.run(["dotnet", "run", "--project", "Verify.CustomNetwork.Yarp",
                                              "--launch-profile", "LocalReverseProxy", "--no-build"],
                                             cwd=custom_root, text=True, capture_output=True, timeout=30,
                                             env=no_certificate)
        require(missing_certificate.returncode != 0 and
                "Custom proxy domains require" in missing_certificate.stderr,
                "custom proxy domains started without a certificate")
        invalid_port = base / "invalid-port"
        rejected = subprocess.run(["dotnet", "new", "casko-umbraco-topology", "--name", "Verify.InvalidPort",
                                   "--output", str(invalid_port), "--cd-port", "65535", "--allow-scripts", "Yes",
                                   "--debug:custom-hive", str(hive)], text=True, capture_output=True, timeout=30)
        require(rejected.returncode != 0 or "Command failed" in rejected.stdout,
                "CD port without a second slot was accepted")
        collision = subprocess.run(["dotnet", "new", "casko-umbraco-topology", "--name", "Verify.Collision",
                                    "--output", str(base / "invalid-collision"), "--cm-port", "44222",
                                    "--cd-port", "44222", "--allow-scripts", "Yes",
                                    "--debug:custom-hive", str(hive)], text=True, capture_output=True, timeout=30)
        require(collision.returncode != 0, "conflicting CM and CD ports were accepted")
        for cache, media, proxy in itertools.product(("redis", "mssql"), ("blob", "filesystem"),
                                                     (False, True)):
            if args.pair and args.pair != f"{cache}+{media}":
                continue
            name = "Verify." + cache.title() + media.title() + ("Proxy" if proxy else "Direct") + ".V" + secrets.token_hex(3)
            root = base / f"{cache}-{media}-{'proxy' if proxy else 'direct'}"
            custom = cache == "mssql" and media == "filesystem"
            command = ["dotnet", "new", "casko-umbraco-topology", "--name", name,
                       "--output", str(root), "--cache-provider", cache, "--media-provider", media,
                       "--debug:custom-hive", str(hive)]
            if proxy:
                command += ["--reverse-proxy"]
            if custom:
                command += ["--admin-email", "verify-admin@example.com", "--admin-password", SECRET_VALUES[0],
                            "--sql-password", SECRET_VALUES[2],
                            "--api-user-email", "verify-api@dev.localhost", "--api-client-id",
                            "umbraco-back-office-verification", "--api-client-secret", SECRET_VALUES[1]]
            run(command)
            web, host = inspect(root, name, cache, media, custom, proxy)
            run(["python3", "scripts/validate-generated.py"], cwd=root)
            require((root / ".local/credentials.env").stat().st_mode & 0o077 == 0,
                    "credential file permissions are too broad")
            if args.runtime:
                inject_failing_health_check(web)
            run(["dotnet", "build", str(root / f"{name}.slnx"), "-v:q", "-clp:ErrorsOnly"])
            inspect_restore(web, cache, media)
            if args.runtime:
                smoke(root, web, host, name, cache == "redis" and media == "blob" or custom, proxy)
            print(f"PASS {cache}+{media}+{'proxy' if proxy else 'direct'}: generated, inspected, built" +
                  (", booted" if args.runtime else ""))


if __name__ == "__main__":
    main()
