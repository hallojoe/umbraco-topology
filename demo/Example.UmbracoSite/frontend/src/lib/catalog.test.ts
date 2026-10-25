import { describe, expect, it } from 'vitest';
import { newestProducts, pastEvents, upcomingEvents, type CatalogItem } from './catalog';

const item = (id: string, date: string): CatalogItem => ({
  id,
  title: id,
  description: id,
  date: new Date(`${date}T00:00:00Z`),
});

describe('catalog order', () => {
  const today = new Date('2026-10-16T18:00:00Z');

  it('shows the nearest upcoming events first, including events today', () => {
    const events = [item('later', '2026-12-01'), item('past', '2026-10-15'), item('today', '2026-10-16')];
    expect(upcomingEvents(events, today).map((entry) => entry.id)).toEqual(['today', 'later']);
    expect(pastEvents(events, today).map((entry) => entry.id)).toEqual(['past']);
  });

  it('shows a clear empty state when no events are upcoming', () => {
    expect(upcomingEvents([item('past', '2026-10-15')], today)).toEqual([]);
  });

  it('shows newly published products first', () => {
    const products = [item('old', '2026-01-01'), item('new', '2026-10-01')];
    expect(newestProducts(products).map((entry) => entry.id)).toEqual(['new', 'old']);
  });
});
