# Umbraco local topology template

Create a local Umbraco 17 solution with one content management node, two content delivery nodes, and Single mode. Aspire runs the services. The template includes a sample site.

## Requirements

Install .NET 10, the Aspire CLI, Python 3, Node.js 22 or newer, and Docker or Podman.

## Install and create a solution

```bash
dotnet new install Casko.UmbracoTopology.Templates
dotnet new casko-umbraco-topology --name Acme.UmbracoSite --output ./Acme.UmbracoSite --allow-scripts Yes
```

The default setup uses Redis cache, Blob media, and Podman. Use `--container-runtime docker` to select Docker. The generated README contains startup commands and all local endpoints.

See the [project guide](https://github.com/hallojoe/umbraco-topology) for options and verification steps. Report problems through the [issue tracker](https://github.com/hallojoe/umbraco-topology/issues).
