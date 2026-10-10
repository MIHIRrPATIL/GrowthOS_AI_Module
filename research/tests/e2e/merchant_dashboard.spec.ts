import { test, expect } from '@playwright/test';

test.describe('GrowthOS Merchant Console & Behavioral Intelligence Flow', () => {
  test('navigates merchant dashboard, inspects funnels, triggers dormant cart recovery, and selects templates', async ({ page }) => {
    // 1. Visit Merchant Dashboard Overview
    await page.goto('http://localhost:4001');
    await expect(page.locator('h1')).toContainText('Behavioral Growth & Funnel Health');
    await expect(page.locator('text=10.97%')).toBeVisible();

    // 2. Navigate to Funnels Page
    await page.click('a[href="/funnels"]');
    await expect(page.locator('h1')).toContainText('Conversion Funnels & Drop-Off Diagnostics');
    await expect(page.locator('text=Granular Checkout (5 Steps)')).toBeVisible();
    await expect(page.locator('text=44.3% Lost at Delivery Slot & Charges')).toBeVisible();

    // 3. Switch to Macro Funnel
    await page.click('button:has-text("Macro Store Funnel")');
    await expect(page.locator('text=Browse → Cart → Checkout → Purchase')).toBeVisible();

    // 4. Navigate to Dormant Carts & Absence Signal Recovery Hub
    await page.click('a[href="/cohorts"]');
    await expect(page.locator('h1')).toContainText('Dormant Carts & Churn Recovery');
    await expect(page.locator('text=Rahul Sharma')).toBeVisible();

    // 5. Open Retention Action Modal for Rahul Sharma
    const triggerBtn = page.locator('button:has-text("Trigger Retention Action")').first();
    await expect(triggerBtn).toBeVisible();
    await triggerBtn.click();

    await expect(page.locator('text=Module 1 & 4 Retention Action')).toBeVisible();
    await expect(page.locator('text=Auto-Waive Delivery Fee (Use 60 Loyalty Pts)')).toBeVisible();

    // Dispatch action
    await page.click('button:has-text("Dispatch Retention Action")');
    await expect(page.locator('text=Action Dispatched')).toBeVisible({ timeout: 8000 });

    // 6. Navigate to Vertical Templates & Modular Switchboard
    await page.click('a[href="/templates"]');
    await expect(page.locator('h1')).toContainText('Vertical Templates & Event Switchboard');
    await expect(page.getByRole('heading', { name: 'E-Commerce & Food Delivery', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'B2B / B2C SaaS Platform', exact: true })).toBeVisible();

    // Select SaaS template
    await page.getByRole('heading', { name: 'B2B / B2C SaaS Platform', exact: true }).click();
    await expect(page.getByText('user.signup').first()).toBeVisible();

    // 7. Navigate to Live Telemetry Stream
    await page.click('a[href="/live-stream"]');
    await expect(page.locator('h1')).toContainText('Live Telemetry & Event Inspector');
    await expect(page.locator('text=purchase.completed')).toBeVisible();

    // 8. Navigate to AI Growth Brain Assistant
    await page.click('a[href="/ai-brain"]');
    await expect(page.locator('h1')).toContainText('AI Growth Brain Assistant');
    await expect(page.getByRole('button', { name: 'Why did checkout conversion' })).toBeVisible();
  });
});
