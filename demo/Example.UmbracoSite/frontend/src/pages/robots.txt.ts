import type { APIRoute } from 'astro';

export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error('The site URL is required to generate robots.txt');

  const isLocal = ['localhost', '127.0.0.1'].includes(site.hostname);
  const body = isLocal
    ? 'User-agent: *\nDisallow: /\n'
    : `User-agent: *\nAllow: /\nSitemap: ${new URL('/sitemap-index.xml', site)}\n`;

  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
