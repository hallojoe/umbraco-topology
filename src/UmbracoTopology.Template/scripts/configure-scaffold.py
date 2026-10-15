#!/usr/bin/env python3
"""Complete port and public URL setup after dotnet new copies the template."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
options = json.loads((root / "scripts/scaffold-options.json").read_text())
proxy_enabled = str(options["reverseProxy"]).lower() == "true"
web = next(root.glob("*.Web/Properties/launchSettings.json"))
host = next(root.glob("*.AppHost/Properties/launchSettings.json"))
profiles_data = json.loads(web.read_text())
profiles = profiles_data["profiles"]
host_profile = json.loads(host.read_text())["profiles"]["Development"]


def port(value, name):
    if not re.fullmatch(r"[0-9]{1,5}", str(value)) or not 1024 <= int(value) <= 65535:
        raise ValueError(f"{name} must be a port from 1024 to 65535")
    return int(value)


def https_port(profile):
    url = profile["applicationUrl"].split(";", 1)[0]
    return urlsplit(url).port


def replace_https_port(profile, new_port):
    old_port = https_port(profile)
    profile["applicationUrl"] = profile["applicationUrl"].replace(
        f"https://localhost:{old_port}", f"https://localhost:{new_port}", 1)


cm_port = port(options["cmPort"], "cm-port") if options["cmPort"] != "auto" else https_port(profiles["SchedulingPublisher"])
cd_port = port(options["cdPort"], "cd-port") if options["cdPort"] != "auto" else https_port(profiles["Subscriber1"])
proxy_port = port(options["proxyPort"], "proxy-port")
if cd_port == 65535:
    raise ValueError("cd-port must leave room for CD2")
for key in ("cmDomain", "cdDomain"):
    domain = options[key]
    labels = domain.split(".")
    if len(domain) > 253 or any(len(label) > 63 or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label) for label in labels):
        raise ValueError(f"{key} must be a DNS hostname")
if options["cmDomain"].lower() == options["cdDomain"].lower():
    raise ValueError("CM and CD domains must differ")

replace_https_port(profiles["SchedulingPublisher"], cm_port)
replace_https_port(profiles["Subscriber1"], cd_port)
replace_https_port(profiles["Subscriber2"], cd_port + 1)

all_ports = []
for profile in profiles.values():
    for url in profile["applicationUrl"].split(";"):
        all_ports.append(urlsplit(url).port)
for url in host_profile["applicationUrl"].split(";"):
    all_ports.append(urlsplit(url).port)
for value in host_profile["environmentVariables"].values():
    if isinstance(value, str) and "localhost:" in value:
        all_ports.append(urlsplit(value).port)
if proxy_enabled:
    all_ports.append(proxy_port)
if len(all_ports) != len(set(all_ports)):
    raise ValueError("Generated or selected ports conflict")

cm_url = f'https://{options["cmDomain"]}:{proxy_port}' if proxy_enabled else f"https://localhost:{cm_port}"
cd_url = f'https://{options["cdDomain"]}:{proxy_port}' if proxy_enabled else f"https://localhost:{cd_port}"
cd2_url = cd_url if proxy_enabled else f"https://localhost:{cd_port + 1}"
for name, profile in profiles.items():
    env = profile["environmentVariables"]
    if name == "SchedulingPublisher":
        public_url = cm_url
    elif name.startswith("Subscriber"):
        public_url = cd_url if proxy_enabled else profile["applicationUrl"].split(";", 1)[0]
    else:
        public_url = profile["applicationUrl"].split(";", 1)[0]
    env["Umbraco__CMS__WebRouting__UmbracoApplicationUrl"] = public_url + "/"
    if name in ("Single", "SchedulingPublisher"):
        env["Umbraco__CMS__Security__BackOfficeHost"] = public_url
    if name != "Single" and proxy_enabled:
        env["UMBRACO_LOCAL_REVERSE_PROXY"] = "true"

web.write_text(json.dumps(profiles_data, indent=2) + "\n")
if proxy_enabled:
    yarp_settings = next(root.glob("*.Yarp/appsettings.Development.json"))
    yarp = json.loads(yarp_settings.read_text())
    clusters = yarp["ReverseProxy"]["Clusters"]
    clusters["cm"]["Destinations"]["default"]["Address"] = f"https://localhost:{cm_port}/"
    for name, destination in (("Subscriber1", "subscriber-1"), ("Subscriber2", "subscriber-2")):
        http_url = profiles[name]["applicationUrl"].split(";", 1)[1]
        clusters["cd"]["Destinations"][destination]["Address"] = http_url + "/"
    yarp_settings.write_text(json.dumps(yarp, indent=2) + "\n")
readme = root / "README.md"
content = readme.read_text()
urls = {
    "__CM_PUBLIC_URL__": cm_url,
    "__CD1_PUBLIC_URL__": cd_url,
    "__CD2_PUBLIC_URL__": cd2_url,
    "__CD1_PRIVATE_URL__": f"https://localhost:{cd_port}",
    "__CD2_PRIVATE_URL__": f"https://localhost:{cd_port + 1}",
    "__SINGLE_PUBLIC_URL__": profiles["Single"]["applicationUrl"].split(";", 1)[0],
}
for token, value in urls.items():
    content = content.replace(token, value)
readme.write_text(content)
print("Configured ports and public URLs.")
