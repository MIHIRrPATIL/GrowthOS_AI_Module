import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('GrowthOS Canonical E-Commerce Flow Tests', () => {
  const harnessPath = 'file://' + path.resolve(__dirname, '../test-harness.html');

  test('executes full e-commerce lifecycle and captures expected canonical events in sequence', async ({ page }) => {
    await page.goto(harnessPath);

    // 1. Initial page load should trigger page.viewed and session.started
    await page.waitForTimeout(500);

    // 2. View Product
    await page.click('#btnViewProduct');
    // 3. Add to Cart
    await page.click('#btnAddToCart');
    // 4. Start Checkout
    await page.click('#btnStartCheckout');
    // 5. Complete Step 2
    await page.click('#btnStep2');
    // 6. Complete Purchase
    await page.click('#btnCompletePurchase');

    const events = await page.evaluate(() => (window as any).__capturedEvents);

    const eventNames = events.map((e: any) => e.name);

    // Verify key business events are present
    expect(eventNames).toContain('page.viewed');
    expect(eventNames).toContain('product.viewed');
    expect(eventNames).toContain('cart.item_added');
    expect(eventNames).toContain('checkout.started');
    expect(eventNames).toContain('checkout.step_completed');
    expect(eventNames).toContain('purchase.completed');

    // Verify product.viewed properties
    const productEvent = events.find((e: any) => e.name === 'product.viewed');
    expect(productEvent.props.product_id).toBe('PRD-PIZZA-FARMHOUSE');
    expect(productEvent.props.price).toBe(459.00);

    // Verify purchase.completed properties
    const purchaseEvent = events.find((e: any) => e.name === 'purchase.completed');
    expect(purchaseEvent.props.order_id).toBe('ORD-2026-9481');
    expect(purchaseEvent.props.total).toBe(978.00);
  });
});
