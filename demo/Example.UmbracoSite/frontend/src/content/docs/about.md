---
title: About
description: Learn why the Example Umbraco Site has a separate static frontend.
---

This site is a small frontend for the Example Umbraco Site topology demo. Astro builds its pages from local Markdown and MDX files. Starlight supplies the page layout, navigation, and search.

The frontend runs as its own Aspire resource. The Umbraco site and its proxy keep their existing routes. A later phase can replace the local content source with the Umbraco Delivery API.
