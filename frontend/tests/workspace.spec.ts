import { test, expect } from "@playwright/test";

test("runs a scenario, saves a snapshot, and restores it after reload", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Save current scenario", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Tétouan, Morocco · 4h / 10% flex",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "INPUT PROFILE", exact: true })
    .selectOption("synthetic");
  await expect(
    page.getByText("Unapplied changes", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(
    page.getByText("Synthetic system", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", {
      name: "Tétouan, Morocco · 4h / 10% flex",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("slider", { name: /Storage duration/ }),
  ).toHaveValue("4");
});

test("applies a heatmap result and replays its dispatch", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Scenario lab 20", exact: true })
    .click();
  await page
    .getByRole("button", { name: /8 hours storage, 20 percent flexibility:/ })
    .click();
  await page
    .getByRole("button", { name: "Use this scenario", exact: true })
    .click();
  await expect(
    page.getByRole("slider", { name: /Storage duration/ }),
  ).toHaveValue("8");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Dispatch replay", exact: true })
    .click();
  await expect(
    page.getByRole("slider", { name: "Replay hour", exact: true }),
  ).toHaveValue("12");
  await page.getByRole("button", { name: "Next hour", exact: true }).click();
  await expect(
    page.getByRole("slider", { name: "Replay hour", exact: true }),
  ).toHaveValue("13");
  await page.getByRole("button", { name: "Play replay", exact: true }).click();
  await expect(
    page.getByRole("slider", { name: "Replay hour", exact: true }),
  ).not.toHaveValue("13");
  await page.getByRole("button", { name: "Pause replay", exact: true }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download all hours", exact: true })
    .click();
  expect((await download).suggestedFilename()).toMatch(
    /gridflex-dispatch-.*\.csv/,
  );
});

test("all compute labs render their real API results without browser errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  for (const [view, heading] of [
    ["Forecasting", "Predictions meet observations"],
    ["Stress test", "How much pressure can the system absorb?"],
    ["Optimizer", "The gap between a rule and foresight"],
  ]) {
    await page.getByRole("button", { name: view, exact: true }).click();
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible({ timeout: 30000 });
  }
  await page
    .getByRole("checkbox", { name: /Restore initial state of charge/ })
    .check();
  await expect(
    page.getByText("Terminal constraints differ from the heuristic", {
      exact: true,
    }),
  ).toBeVisible({ timeout: 30000 });
  expect(errors).toEqual([]);
});

test("supports mobile navigation and configuration without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Configure", exact: true }).click();
  await page.getByRole("button", { name: "14d", exact: true }).click();
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(
    page.getByText("14-DAY HORIZON", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  await page.getByRole("button", { name: "Stress test", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "How much pressure can the system absorb?",
      exact: true,
    }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("handles short forecast history and exports a versioned scenario", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export run", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/gridflex-.*\.json/);
  await page.getByRole("button", { name: "7d", exact: true }).click();
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(
    page.getByText("Simulation ready", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Forecasting", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Give the model a little more history",
      exact: true,
    }),
  ).toBeVisible();
});
