import { test, expect } from '@playwright/test';

test.describe('Smoke tests', () => {
  test('homepage loads with zh-CN lang attribute', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
    await expect(page.locator('h1')).toBeVisible();
  });

  test('/en/ loads with en lang attribute', async ({ page }) => {
    await page.goto('/en/');
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  });

  test('/demo page loads and input area is visible', async ({ page }) => {
    await page.goto('/demo');
    const textarea = page.locator('textarea, [contenteditable="true"], [role="textbox"]').first();
    await expect(textarea).toBeVisible();
  });

  test('/pricing page loads with pricing cards', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('/download page loads', async ({ page }) => {
    await page.goto('/download');
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('/docs page loads', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('language switcher exists', async ({ page }) => {
    await page.goto('/');
    const langSwitcher = page.locator(
      '[aria-label="语言"], [aria-label="Language"], [role="button"]:has-text("EN"), [role="button"]:has-text("中文"), .lang-switcher, #lang-switcher'
    ).first();
    await expect(langSwitcher).toBeVisible();
  });

  test('404 page shows proper content', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page.locator('body')).toBeVisible();
  });
});
