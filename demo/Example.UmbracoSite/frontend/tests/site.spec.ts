import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const routes = [
  '/',
  '/events/',
  '/products/',
  '/about/',
  '/events/community-meetup/',
  '/events/product-showcase/',
  '/events/workshop-day/',
  '/products/starter-pack/',
  '/products/field-kit/',
  '/products/reference-cards/',
];

for (const route of routes) {
  test(`${route} loads with metadata and no accessibility violations`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.ok()).toBeTruthy();
    await expect(page.locator('main h1')).toHaveCount(1);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /\S/);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });
}

test('home links to the nearest events and newest products', async ({ page }) => {
  await page.goto('/');
  const upcoming = page.locator('#latest-events + ul li');
  expect(await upcoming.count()).toBeLessThanOrEqual(2);
  if (await upcoming.count()) {
    const dates = await upcoming.locator('time').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('datetime')));
    expect(dates).toEqual([...dates].sort());
  } else {
    await expect(page.getByText('No upcoming events.')).toBeVisible();
  }
  await expect(page.locator('#latest-products + ul li')).toHaveCount(2);
  await expect(page.getByRole('link', { name: 'Reference cards' })).toHaveAttribute('href', '/products/reference-cards/');
});
