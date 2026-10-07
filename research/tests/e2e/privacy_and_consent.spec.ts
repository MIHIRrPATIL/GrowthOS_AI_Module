import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('GrowthOS Privacy, Masking & Consent Compliance', () => {
  const harnessPath = 'file://' + path.resolve(__dirname, '../test-harness.html');

  test('masks credit card numbers and passwords in tracked property payloads', async ({ page }) => {
    await page.goto(harnessPath);

    // Track an event containing a credit card number and password
    await page.evaluate(() => {
      (window as any).GrowthOS.track('custom_test_event', {
        credit_card: '4111 1111 1111 1111',
        password: 'mySecretPassword123!',
        user_notes: 'Customer mentioned card 4111 1111 1111 1111 in chat',
        plain_text: 'Regular non-sensitive information'
      });
    });

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const customEvent = events.find((e: any) => e.name === 'custom_test_event');

    expect(customEvent).toBeDefined();
    expect(customEvent.props.password).toBe('[REDACTED]');
    expect(customEvent.props.credit_card).toBe('[REDACTED]');
    expect(customEvent.props.user_notes).toBe('Customer mentioned card [CARD_ENDED_1111] in chat');
    expect(customEvent.props.plain_text).toBe('Regular non-sensitive information');
  });

  test('ceases event tracking when user opts out of consent', async ({ page }) => {
    await page.goto(harnessPath);

    // Opt out
    await page.evaluate(() => (window as any).GrowthOS.optOut());

    const countBefore = await page.evaluate(() => (window as any).__capturedEvents.length);

    // Try to view product and click
    await page.click('#btnViewProduct');
    await page.click('#btnAddToCart');

    const countAfter = await page.evaluate(() => (window as any).__capturedEvents.length);

    // No new events should have fired
    expect(countAfter).toBe(countBefore);

    // Opt back in
    await page.evaluate(() => (window as any).GrowthOS.optIn());
    await page.click('#btnViewProduct');

    const countAfterOptIn = await page.evaluate(() => (window as any).__capturedEvents.length);
    expect(countAfterOptIn).toBeGreaterThan(countBefore);
  });
});
