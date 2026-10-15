---
name: umbraco-automate
description: Install or configure Umbraco Automate workflows and add-ons in an existing Umbraco project. Use for event-driven automation in the backoffice; not for CM/CD topology or unrelated background jobs.
---

# Umbraco Automate

Inspect the project's CMS version, package references, database provider, existing automation packages, and package management convention. Use the [official installation guide](https://docs.umbraco.com/umbraco-automate/getting-started/installation) and [official repository](https://github.com/umbraco/Umbraco.Automate) to verify supported CMS versions, installation steps, and current API behavior. The current guide requires Umbraco 17.1 or later. Preserve the project's CMS major. If no compatible Automate release is available, stop with a concrete compatibility message.

Install `Umbraco.Automate` when the user asks only for Automate. Add a connector or add-on only when requested for a specific workflow. Configure its database using the project's current convention: a dedicated `umbracoAutomateDbDSN` when one exists or is requested, or `Umbraco:Automate:UseNamedConnectionString=umbracoDbDSN` for a simple local setup that shares the CMS database. The latter also adds automation traffic to the CMS database. Follow the [configuration guide](https://docs.umbraco.com/umbraco-automate/getting-started/configuration) and preserve existing Automate data. For a workflow request, establish its trigger, conditions, actions, failure behavior, and any external connection before implementing it. Keep credentials in the project's existing secret mechanism, not tracked settings. Do not create sample automations that might send messages, publish content, or call external endpoints without user intent.

For an existing CM/CD topology, follow [Automate's load balancing guidance](https://docs.umbraco.com/umbraco-automate/run-in-production/load-balancing). Keep the default `SchedulerOnly` execution mode so the `Single` or `SchedulingPublisher` runs steps, while all nodes may capture events into the shared outbox. Verify role and application URL detection. Actions with external side effects should tolerate retries. Do not introduce another Aspire service solely from an example setup.

Build the solution and verify the requested backoffice capability. For a requested workflow, test its trigger and observable result with safe local data. Report any required external credentials, license, or runtime checks that could not be completed.
