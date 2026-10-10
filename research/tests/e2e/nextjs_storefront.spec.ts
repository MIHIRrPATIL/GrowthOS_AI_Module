import { test, expect } from '@playwright/test';

test.describe('GrowthOS Next.js E-Commerce Storefront Flow', () => {
  test('navigates storefront, customizes pizza, applies coupon, and completes purchase', async ({ page }) => {
    // 1. Visit the home storefront
    await page.goto('http://localhost:4000');
    await expect(page.locator('h1')).toContainText('Hot & Fresh Pizzas');

    // 2. Search for Farmhouse
    const searchInput = page.locator('input[name="search_pizzas"]');
    await searchInput.fill('Farmhouse');
    await expect(page.locator('text=Farmhouse')).toBeVisible();

    // 3. Open customizer for Farmhouse
    const customizeBtn = page.locator('button[title="Customize toppings and cheese"]').first();
    await customizeBtn.click();

    // 4. In customizer: select Medium size & Extra Cheese
    const modal = page.locator('.fixed.inset-0.z-50');
    await expect(modal.locator('text=Customize Your Pizza')).toBeVisible();
    await modal.locator('button:has-text("Medium")').click();
    await modal.locator('text=Extra Mozzarella Cheese').click();
    await modal.locator('button:has-text("Add to Cart")').click();

    // 5. Verify Cart Drawer opened with item
    const drawer = page.locator('.fixed.inset-y-0.right-0');
    await expect(drawer.locator('text=Your Order')).toBeVisible();
    await expect(drawer.locator('h4:has-text("Farmhouse")')).toBeVisible();

    // 6. Apply Coupon DOMINOS50
    const couponInput = drawer.locator('input[name="coupon_code"]');
    await couponInput.fill('DOMINOS50');
    await drawer.locator('button:has-text("Apply")').click();
    await expect(drawer.locator('text=Coupon DOMINOS50 applied successfully!')).toBeVisible();

    // 7. Proceed to checkout
    await drawer.locator('button:has-text("Proceed to Checkout")').click();
    await expect(page).toHaveURL(/.*checkout/);

    // 8. Step 1: Fill Delivery Address & submit
    await expect(page.locator('text=Delivery Address & Contact')).toBeVisible();
    await page.click('button:has-text("Continue to Delivery Options")');

    // 9. Step 2: Review Delivery Options & Proceed to Payment
    await expect(page.locator('text=Delivery Slot & Charges')).toBeVisible();
    const proceedToPaymentBtn = page.locator('button:has-text("Proceed to Payment")');
    await expect(proceedToPaymentBtn).toBeVisible();
    await proceedToPaymentBtn.click();

    // 10. Step 3: Confirm order with UPI
    await expect(page.locator('text=Select Payment Method')).toBeVisible();
    const confirmOrderBtn = page.locator('button:has-text("Confirm Order")');
    await expect(confirmOrderBtn).toBeVisible();
    await confirmOrderBtn.click();

    // 11. Verify Order Success & Live Pizza Tracker
    await expect(page).toHaveURL(/.*order\/DOM-/);
    await expect(page.locator('h1')).toContainText('Order Confirmed!');
    await expect(page.locator('text=Live Domino\'s Tracker')).toBeVisible();
    await expect(page.locator('text=+35 Gold Loyalty Points Earned!')).toBeVisible();
  });
});
