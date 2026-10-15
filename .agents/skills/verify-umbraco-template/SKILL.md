---
name: verify-umbraco-template
description: Verify this repository's Umbraco topology template across cache, media, and proxy variants.
---

# Verify Umbraco topology template

Run `python3 .agents/skills/verify-umbraco-template/scripts/verify_template.py` from the repository root.

The default run generates and builds eight combinations. Each cache and media pair runs with and without YARP. Use `--pair redis+blob`, `--pair redis+filesystem`, `--pair mssql+blob`, or `--pair mssql+filesystem` to select one pair. This mode needs Python 3 and .NET 10.

Use `--runtime` for live checks. It starts each cluster, checks content, media, Mailpit, public routing, and health endpoints. It then restarts in Single mode. It also checks MCP for two credential sets. This mode needs Aspire CLI, Node.js, and Podman.

Use `--single-smoke` for the CI smoke test. It starts one default Single project and checks content, media, Mailpit, MCP, and telemetry. Docker is the default container runtime. Use `--smoke-container-runtime podman` for local Podman testing.

The script uses temporary directories and removes its generated projects. Fix failures in the template source, then rerun the relevant check. Report which combinations passed and whether runtime checks ran.
