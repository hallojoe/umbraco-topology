---
name: umbraco-simple-site
description: Copy the packaged simple-site uSync snapshot and HomePage/ContentPage Razor views into an existing Umbraco web project. Use when asked to create a simple Umbraco site, directly or from another skill; this skill only copies assets.
---

# Umbraco simple site

Copy [the packaged uSync snapshot](assets/uSync/) and [the two Razor views](assets/Views/) into one Umbraco web project. The snapshot is under `v17`; copy it unchanged regardless of the target's Umbraco version. Do not install or configure uSync, edit the snapshot, trigger an import, or change other project files.

## Select the target

Use the folder or `.csproj` named by the user. When another skill invokes this skill, pass that skill's selected Umbraco web project. If neither provides a target, the copy helper looks for an Umbraco.Cms project in the current directory or its ancestors, then for a unique project beneath the current directory. If it reports multiple candidates, show those paths and ask which project to use; do not guess.

## Copy

Run `python3 <skill-directory>/scripts/copy_assets.py [target-folder-or-csproj]` from the caller's working directory. The helper checks every destination before writing. If a uSync folder or either packaged view already exists, it exits without changes. Use `--overwrite` only when overwrite was requested; this replaces the entire target uSync folder and the two packaged view files while preserving other views. Never bypass the helper's collision check.

Report the selected project and what was copied. An import and any runtime compatibility check are separate target-project work, not part of this skill.
