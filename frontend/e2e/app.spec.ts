import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('App loads and renders', () => {
  test('app loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/');
    await expect(page.locator('h1')).toHaveText('Prototype — Accessible Video Review');
    // Wait for initial render
    await page.waitForTimeout(1000);

    // Filter out common non-app errors
    const appErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('Failed to load resource'),
    );
    expect(appErrors).toEqual([]);
  });

  test('page has semantic landmarks', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('header')).toBeVisible();
  });

  test('all major sections are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Process a video")')).toBeVisible();
    await expect(page.locator('h2:has-text("Processed jobs")')).toBeVisible();
    await expect(page.locator('h2:has-text("Accessibility settings")')).toBeVisible();
    await expect(page.locator('h2:has-text("Video player")')).toBeVisible();
    await expect(page.locator('h2:has-text("Scene description")')).toBeVisible();
    await expect(page.locator('h2:has-text("Summary and navigation")')).toBeVisible();
  });
});

test.describe('Accessibility - axe-core', () => {
  test('empty state has no critical or serious a11y violations', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    expect(violations).toEqual([]);
  });

  test('interactive controls have accessible names', async ({ page }) => {
    await page.goto('/');

    const buttons = page.locator('button:visible');
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      const button = buttons.nth(i);
      const accessibleName = await button.getAttribute('aria-label');
      const textContent = await button.textContent();
      const hasName = accessibleName || (textContent && textContent.trim().length > 0);
      expect(hasName).toBeTruthy();
    }
  });
});

test.describe('Keyboard shortcuts', () => {
  test('Space/K play/pause keyboard shortcuts are defined in UI hint', async ({ page }) => {
    await page.goto('/');
    const hint = page.locator('.keyboard-hint');
    await expect(hint).toContainText('Space');
    await expect(hint).toContainText('K');
  });

  test.describe('job not loaded', () => {
    test('D key does not cause errors', async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(500);

      // Focus the body so keyboard handler fires
      await page.locator('body').focus();
      await page.keyboard.press('d');
      await page.waitForTimeout(300);
      // Should still show the empty state description
      await expect(page.locator('.description-text')).toBeVisible();
    });
  });
});

test.describe('Accessibility panel', () => {
  test('font size buttons have accessible names', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('button[aria-label="Decrease interface text size"]')).toBeVisible();
    await expect(page.locator('button[aria-label="Increase interface text size"]')).toBeVisible();
  });

  test('dyslexia font toggle has aria-pressed', async ({ page }) => {
    await page.goto('/');
    const btn = page.locator('button:has-text("Dyslexia font")');
    await expect(btn).toHaveAttribute('aria-pressed', 'false');
    await btn.click();
    await expect(btn).toHaveAttribute('aria-pressed', 'true');
  });

  test('high contrast toggle changes CSS', async ({ page }) => {
    await page.goto('/');
    const btn = page.locator('button:has-text("High contrast")');
    await btn.click();
    // HTML element should have high-contrast class
    await expect(page.locator('html')).toHaveClass(/high-contrast/);
  });
});

test.describe('Summary tabs', () => {
  test('tabs have correct ARIA roles', async ({ page }) => {
    await page.goto('/');
    const tabs = page.locator('[role="tab"]');
    await expect(tabs).toHaveCount(3);
    await expect(tabs.first()).toHaveAttribute('aria-selected', 'true');
  });

  test('ArrowRight moves to next tab', async ({ page }) => {
    await page.goto('/');
    const summaryTab = page.locator('[role="tab"]:has-text("Summary")');
    await summaryTab.focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.locator('[role="tab"]:has-text("Chapters")')).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  test('ArrowLeft wraps to last tab', async ({ page }) => {
    await page.goto('/');
    const summaryTab = page.locator('[role="tab"]:has-text("Summary")');
    await summaryTab.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('[role="tab"]:has-text("Scenes")')).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  test('Home goes to first tab', async ({ page }) => {
    await page.goto('/');
    // First click scenes tab
    await page.locator('[role="tab"]:has-text("Scenes")').click();
    const scenesTab = page.locator('[role="tab"]:has-text("Scenes")');
    await scenesTab.focus();
    await page.keyboard.press('Home');
    await expect(page.locator('[role="tab"]:has-text("Summary")')).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  test('End goes to last tab', async ({ page }) => {
    await page.goto('/');
    const summaryTab = page.locator('[role="tab"]:has-text("Summary")');
    await summaryTab.focus();
    await page.keyboard.press('End');
    await expect(page.locator('[role="tab"]:has-text("Scenes")')).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });
});

test.describe('Player controls', () => {
  test('player controls are visible when no job is loaded', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('button[aria-label="Play"]')).toBeVisible();
    await expect(page.locator('button[aria-label="Describe current scene"]')).toBeVisible();
  });

  test('speed selector has all options', async ({ page }) => {
    await page.goto('/');
    const speed = page.locator('[aria-label="Playback speed"]');
    await expect(speed.locator('option')).toHaveCount(6);
  });

  test('subtitle mode selector has three options', async ({ page }) => {
    await page.goto('/');
    const mode = page.locator('[aria-label="Subtitle mode"]');
    await expect(mode.locator('option')).toHaveCount(3);
  });
});

test.describe('Process panel', () => {
  test('process form has file input and path input', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#videoFileInput')).toBeVisible();
    await expect(page.locator('#videoPathInput')).toBeVisible();
    await expect(page.locator('#processLanguage')).toBeVisible();
  });

  test('start processing button is present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('button:has-text("Start processing")')).toBeVisible();
  });
});

test.describe('Job panel', () => {
  test('job select is present with no jobs message', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=No jobs yet.')).toBeVisible();
  });

  test('refresh button is present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('button[aria-label="Refresh job list"]')).toBeVisible();
  });
});

test.describe('Responsive layout', () => {
  test('no horizontal overflow at desktop width', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(500);

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1);
  });

  test('page renders at tablet width without breaking', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForTimeout(500);

    // All panels should still be visible
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('text=Video player')).toBeVisible();
  });

  test('page renders at mobile width without breaking', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');
    await page.waitForTimeout(500);

    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('text=Video player')).toBeVisible();
  });
});
