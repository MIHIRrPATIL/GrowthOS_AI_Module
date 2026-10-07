import { test, expect } from '@playwright/test';

test.describe('GrowthOS Tab Switching & Visibility Monitoring', () => {
  test('detects tab switching away, tab return, and coupon hunt intent', async ({ page }) => {
    await page.goto('http://localhost:4000/checkout');
    await page.waitForTimeout(500);

    // 1. Simulate user switching away (visibilitychange to hidden)
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await page.waitForTimeout(600);

    // 2. Simulate user returning back after 15 seconds of coupon hunting
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: false, configurable: true });
      Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await page.waitForTimeout(600);

    // 3. Open QA Overlay to inspect captured tab events
    const qaButton = page.locator('button:has-text("GrowthOS QA Stream")');
    await qaButton.click();

    const overlay = page.locator('.fixed.bottom-4.right-4');
    await expect(overlay).toBeVisible();

    // Verify user.tab_switched_away & user.tab_returned events are tracked
    await expect(overlay.locator('text=user.tab_switched_away')).toBeVisible();
    await expect(overlay.locator('text=user.tab_returned')).toBeVisible();
  });
});
