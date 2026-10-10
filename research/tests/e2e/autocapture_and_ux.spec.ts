import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('GrowthOS Autocapture, Forms & UX Friction Tests', () => {
  const harnessPath = 'file://' + path.resolve(__dirname, '../test-harness.html');

  test('captures form interactions across started, focused, blurred, and changed', async ({ page }) => {
    await page.goto(harnessPath);

    // Focus on name input
    await page.fill('#nameInput', 'Alice Smith');
    await page.focus('#emailInput');
    await page.fill('#emailInput', 'alice@growthos.io');
    await page.click('#btnSubmitForm');

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const eventNames = events.map((e: any) => e.name);

    expect(eventNames).toContain('form.started');
    expect(eventNames).toContain('form.field_focused');
    expect(eventNames).toContain('form.field_changed');
    expect(eventNames).toContain('form.submitted');
  });

  test('detects rapid rage clicks on an element', async ({ page }) => {
    await page.goto(harnessPath);

    const btn = page.locator('#btnRageClick');
    // Rapid clicks within 200ms
    await btn.click();
    await btn.click();
    await btn.click();
    await page.waitForTimeout(300);

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const rageEvent = events.find((e: any) => e.name === 'user.rage_click');

    expect(rageEvent).toBeDefined();
    expect(rageEvent.props.click_count).toBeGreaterThanOrEqual(3);
    expect(rageEvent.props.element_id).toBe('btnRageClick');
  });

  test('captures scroll milestones as user scrolls down the page', async ({ page }) => {
    await page.goto(harnessPath);

    // Scroll down to 50% and 100%
    await page.evaluate(() => window.scrollTo(0, 1200));
    await page.waitForTimeout(300);
    await page.evaluate(() => window.scrollTo(0, 2500));
    await page.waitForTimeout(300);

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const scrollEvents = events.filter((e: any) => e.name === 'scroll.milestone');

    expect(scrollEvents.length).toBeGreaterThan(0);
    const milestones = scrollEvents.map((e: any) => e.props.milestone_percentage);
    expect(milestones).toContain(25);
  });
});
