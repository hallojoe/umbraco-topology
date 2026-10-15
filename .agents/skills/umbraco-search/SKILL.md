---
name: umbraco-search
description: Add or configure the new Umbraco Search package and a compatible search provider in an Umbraco project. Use for Umbraco Search indexing, backoffice search, or frontend search; not for the older built-in Examine API alone.
---

# Umbraco Search

Add the new provider-based Umbraco Search to a project that already has Umbraco. Inspect the effective CMS version, installed search packages, current search implementation, and package management convention before editing. Check the current [Umbraco Search installation guide](https://docs.umbraco.com/umbraco-search/installation/installation) and [official repository](https://github.com/umbraco/Umbraco.Cms.Search) for compatible package versions and APIs; the product is evolving. Preserve the project's CMS major and pin mutually compatible Search packages. Stop with a compatibility message if no supported release exists for that major.

Determine the requested outcome: package installation, backoffice search, frontend query, Delivery API search, or a combination. For basic functionality, add `Umbraco.Cms.Search.Core` and the official `Umbraco.Cms.Search.Provider.Examine`, then register `AddSearchCore()` and `AddExamineSearchProvider()` in a composer using the APIs for the selected version. Add `Umbraco.Cms.Search.BackOffice` with `AddBackOfficeSearch()` or `Umbraco.Cms.Search.DeliveryApi` with `AddDeliveryApiSearch()` only when those surfaces are requested. If the user names another provider, verify its current package and capabilities before adding it. Keep existing custom Examine indexes and queries unless the requested change requires a migration. Do not silently replace the site's current search experience.

For a CM/CD topology, verify which processes create and read indexes and use each process's local index location or a provider-supported shared service. Account for publish/update propagation and rebuild behavior. Do not add a new Aspire resource for the default Examine provider merely because the site uses Aspire. Follow provider-specific infrastructure guidance if a different provider requires a service.

Build the solution. Where a running site and suitable content exist, index a published item and show that the requested search surface returns it; check that draft or protected content is not exposed publicly. Report any runtime check that could not be performed and any provider or beta limitation relevant to the selected version.
