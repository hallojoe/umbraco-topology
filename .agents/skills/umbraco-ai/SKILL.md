---
name: umbraco-ai
description: Add or configure Umbraco AI packages, providers, prompts, or agents in an existing Umbraco project. Use for Umbraco AI features and integrations; not for general AI SDK work outside Umbraco.
---

# Umbraco AI

Inspect the effective CMS version, current Umbraco AI packages, project configuration, and package management convention. Check the [official Umbraco AI documentation](https://docs.umbraco.com/ai-in-umbraco) and [official repository](https://github.com/umbraco/Umbraco.AI) for package compatibility and current provider APIs. The current documentation requires Umbraco 17.1 or later. Preserve the project's CMS major and use compatible, pinned packages. Stop with a concrete compatibility message when the requested package does not support that version.

Determine whether the user wants only the core AI integration, a particular provider, or a functional feature such as prompts, agents, or backoffice tools. Follow the [installation guide](https://docs.umbraco.com/ai-in-umbraco/getting-started/installation) to add `Umbraco.AI`; a functional installation also needs a provider package such as `Umbraco.AI.OpenAI`. A working AI feature needs a selected provider, model, and authentication method; infer these from existing project settings or the user's request, and ask for missing choices that affect functionality. Install only the relevant official provider and feature packages. Do not make OpenAI or any other paid service a default. Do not hardcode API keys, send them to logs, or commit them to source control; use the project's secret mechanism.

For CM/CD, keep authoring and backoffice-only features on the appropriate role when the product supports role-specific registration. Add an Aspire resource only for a selected local service or emulator actually required by the chosen provider. Avoid adding an unrelated local model service by default.

Build the solution. Verify package registration and the requested feature. Run a live model call only when credentials and authorization are available; report untested external integration clearly. Document the chosen provider, model, secret setting name, and any expected usage cost without revealing credentials.
