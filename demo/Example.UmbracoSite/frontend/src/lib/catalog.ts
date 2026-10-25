export interface CatalogItem {
  id: string;
  title: string;
  description: string;
  date: Date;
}

export function upcomingEvents(items: CatalogItem[], today = new Date()): CatalogItem[] {
  const startOfToday = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return items
    .filter((item) => item.date.valueOf() >= startOfToday)
    .sort((a, b) => a.date.valueOf() - b.date.valueOf() || a.id.localeCompare(b.id));
}

export function pastEvents(items: CatalogItem[], today = new Date()): CatalogItem[] {
  const startOfToday = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return items
    .filter((item) => item.date.valueOf() < startOfToday)
    .sort((a, b) => b.date.valueOf() - a.date.valueOf() || a.id.localeCompare(b.id));
}

export function newestProducts(items: CatalogItem[]): CatalogItem[] {
  return [...items].sort(
    (a, b) => b.date.valueOf() - a.date.valueOf() || a.id.localeCompare(b.id),
  );
}
