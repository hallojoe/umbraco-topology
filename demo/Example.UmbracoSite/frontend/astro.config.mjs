import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: process.env.SITE_URL ?? 'http://localhost:4321',
  integrations: [
    starlight({
      title: 'Example Umbraco Site',
      description: 'A small catalog of events and products for the Umbraco topology demo.',
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { slug: '' },
        { slug: 'events' },
        { slug: 'products' },
        { slug: 'about' },
      ],
    }),
  ],
});
