import { test, expect } from "@playwright/test";

for (const failure of ["busy", "non-json server error", "network"] as const) {
  test(`recovers from ${failure} without reloading the workspace`, async ({
    page,
  }) => {
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    const detail = "The simulation engine is busy. Try again shortly.";
    let failedSettings: unknown;
    let navigationsAfterFailure = 0;

    // Fail every initial request so React's development/strict effects cannot
    // consume a one-shot fault. The retry below reaches the real API.
    await page.route("**/api/simulate", async (route) => {
      failedSettings = route.request().postDataJSON();
      if (failure === "network") return route.abort("failed");
      await route.fulfill({
        status: failure === "busy" ? 503 : 502,
        contentType: failure === "busy" ? "application/json" : "text/html",
        body:
          failure === "busy"
            ? JSON.stringify({ detail })
            : "<h1>Bad gateway</h1>",
        headers: failure === "busy" ? { "Retry-After": "2" } : {},
      });
    });
    await test.step("Given a failed simulation, show an actionable error", async () => {
      await page.goto("/");
      const alert = page.getByRole("alert");
      await expect(alert).toBeVisible();
      if (failure === "busy") await expect(alert).toContainText(detail);
      if (failure === "non-json server error")
        await expect(alert).toContainText("Simulation unavailable (502)");
      if (failure === "network")
        await expect(alert).toContainText("Failed to fetch");
      await expect(
        page.getByText("Simulation ready", { exact: true }),
      ).toHaveCount(0);
      page.on("framenavigated", (frame) => {
        if (frame === page.mainFrame()) navigationsAfterFailure += 1;
      });
    });
    await test.step("When connectivity recovers, retry the same settings", async () => {
      await page.unroute("**/api/simulate");
      const response = page.waitForResponse(
        (response) =>
          response.url().endsWith("/api/simulate") &&
          response.request().method() === "POST",
      );
      await page
        .getByRole("button", { name: "Try again", exact: true })
        .click();
      const retried = await response;
      expect(retried.status()).toBe(200);
      expect(retried.request().postDataJSON()).toEqual(failedSettings);
    });
    await test.step("Then real results replace the error without a reload", async () => {
      await expect(
        page.getByText("Simulation ready", { exact: true }),
      ).toBeVisible();
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: "Export run", exact: true }),
      ).toBeEnabled();
      expect(browserErrors).toEqual([]);
      expect(navigationsAfterFailure).toBe(0);
    });
  });
}
