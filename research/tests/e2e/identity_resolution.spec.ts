import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('GrowthOS Identity Resolution & Session Boundaries', () => {
  const harnessPath = 'file://' + path.resolve(__dirname, '../test-harness.html');

  test('maintains stable anonymous_id and links customer_id upon identify()', async ({ page }) => {
    await page.goto(harnessPath);

    const initialAnonId = await page.evaluate(() => (window as any).GrowthOS.getAnonymousId());
    expect(initialAnonId).toMatch(/^anon_/);

    const initialCustId = await page.evaluate(() => (window as any).GrowthOS.getCustomerId());
    expect(initialCustId).toBeNull();

    // Identify user
    await page.click('#btnIdentify');

    const updatedCustId = await page.evaluate(() => (window as any).GrowthOS.getCustomerId());
    expect(updatedCustId).toBe('CUST-48291');

    // Anonymous ID should remain stable
    const postIdentifyAnonId = await page.evaluate(() => (window as any).GrowthOS.getAnonymousId());
    expect(postIdentifyAnonId).toBe(initialAnonId);

    // Reset / Logout
    await page.click('#btnReset');

    const resetCustId = await page.evaluate(() => (window as any).GrowthOS.getCustomerId());
    expect(resetCustId).toBeNull();
  });
});
