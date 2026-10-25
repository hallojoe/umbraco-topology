import { getCollection } from 'astro:content';
import type { CatalogItem } from './catalog';

export async function getEvents(): Promise<CatalogItem[]> {
  const entries = await getCollection('docs', ({ id }) => id.startsWith('events/'));
  return entries.map(({ id, data }) => {
    if (!data.eventDate) throw new Error(`Missing eventDate: ${id}`);
    return { id, title: data.title, description: data.description, date: data.eventDate };
  });
}

export async function getProducts(): Promise<CatalogItem[]> {
  const entries = await getCollection('docs', ({ id }) => id.startsWith('products/'));
  return entries.map(({ id, data }) => {
    if (!data.publishedAt) throw new Error(`Missing publishedAt: ${id}`);
    return { id, title: data.title, description: data.description, date: data.publishedAt };
  });
}
