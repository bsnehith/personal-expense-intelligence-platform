import { test, expect } from '@playwright/test'

test('dashboard loads and shows app shell', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Expense IQ')).toBeVisible()
})

test('live feed screen can be opened', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: /live feed/i }).click()
  await expect(page.getByText('Live transaction feed')).toBeVisible()
})
