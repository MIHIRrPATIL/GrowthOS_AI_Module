import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('GrowthOS Keystroke Dynamics & Sensitive Field Masking', () => {
  const harnessPath = 'file://' + path.resolve(__dirname, '../test-harness.html');

  test('captures typing dynamics on non-sensitive input fields', async ({ page }) => {
    await page.goto(harnessPath);

    // Focus on name input and type with keystrokes
    const nameInput = page.locator('#nameInput');
    await nameInput.click();
    await nameInput.pressSequentially('Alexander', { delay: 50 });
    // Blur input
    await page.click('#btnSubmitForm');

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const typingEvent = events.find((e: any) => e.name === 'user.typing_dynamics');

    expect(typingEvent).toBeDefined();
    expect(typingEvent.props.field_name).toBe('user_name');
    expect(typingEvent.props.keystroke_count).toBeGreaterThanOrEqual(9);
    expect(typingEvent.props.typing_speed_cpm).toBeGreaterThan(0);
  });

  test('detects excessive corrections friction when user repeatedly hits backspace', async ({ page }) => {
    await page.goto(harnessPath);

    const nameInput = page.locator('#nameInput');
    await nameInput.click();
    await nameInput.pressSequentially('WrongText', { delay: 40 });
    // Hit backspace 6 times
    for (let i = 0; i < 6; i++) {
      await nameInput.press('Backspace');
    }
    await page.click('#btnSubmitForm');

    const events = await page.evaluate(() => (window as any).__capturedEvents);
    const correctionEvent = events.find((e: any) => e.name === 'user.excessive_corrections');

    expect(correctionEvent).toBeDefined();
    expect(correctionEvent.props.backspace_count).toBeGreaterThanOrEqual(5);
  });

  test('strictly suppresses keystroke dynamics and masks sensitive input fields', async ({ page }) => {
    await page.goto(harnessPath);

    // 1. Interact with password field
    const passInput = page.locator('#passwordInput');
    await passInput.click();
    await passInput.pressSequentially('VerySecretPassword!', { delay: 50 });
    await page.click('#btnSubmitForm');

    // 2. Interact with card input
    const cardInput = page.locator('#cardInput');
    await cardInput.click();
    await cardInput.pressSequentially('4111222233334444', { delay: 50 });
    await page.click('#btnSubmitForm');

    // 3. Interact with custom masked input
    const maskedInput = page.locator('#maskedInput');
    await maskedInput.click();
    await maskedInput.pressSequentially('TopSecret123', { delay: 50 });
    await page.click('#btnSubmitForm');

    const events = await page.evaluate(() => (window as any).__capturedEvents);

    // Verify typing dynamics were NEVER recorded for password, card, or masked field
    const sensitiveTyping = events.filter((e: any) =>
      e.name === 'user.typing_dynamics' &&
      (e.props.field_name === 'password' || e.props.field_name === 'card_number' || e.props.field_name === '[SENSITIVE_FIELD]')
    );
    expect(sensitiveTyping.length).toBe(0);

    // Verify form events for sensitive fields masked the field name and value
    const formChanged = events.filter((e: any) => e.name === 'form.field_changed' && e.props.is_sensitive === true);
    expect(formChanged.length).toBeGreaterThanOrEqual(3);
    for (const evt of formChanged) {
      expect(evt.props.field_name).toBe('[SENSITIVE_FIELD]');
      expect(evt.props.value_length).toBe(0);
    }
  });
});
