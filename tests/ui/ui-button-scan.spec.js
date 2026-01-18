const { test } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const OUTPUT_DIR = process.env.UI_ARTIFACTS_DIR || "/opt/cursor/artifacts";
const BUTTON_LOG_PATH = path.join(OUTPUT_DIR, "ui-button-scan.json");
const MAX_TRIAL_CLICKS = Number(process.env.MAX_TRIAL_CLICKS || 120);

const defaultPassword = process.env.TEST_DEFAULT_PASSWORD || "123456";

const roles = [
  {
    key: "system-admin",
    label: "مدير النظام",
    email: process.env.TEST_SYSTEM_ADMIN_EMAIL || "admin@system.com",
    password: process.env.TEST_SYSTEM_ADMIN_PASSWORD || defaultPassword,
    path: "/system-admin",
    waitText: "لوحة تحكم مدير النظام",
  },
  {
    key: "procurement-manager",
    label: "مدير المشتريات",
    email: process.env.TEST_PROCUREMENT_MANAGER_EMAIL || "notofall@gmail.com",
    password: process.env.TEST_PROCUREMENT_MANAGER_PASSWORD || defaultPassword,
    path: "/procurement",
    waitText: "نظام طلبات المواد",
  },
  {
    key: "general-manager",
    label: "المدير العام",
    email: process.env.TEST_GENERAL_MANAGER_EMAIL || "md@test.com",
    password: process.env.TEST_GENERAL_MANAGER_PASSWORD || defaultPassword,
    path: "/general-manager",
    waitText: "لوحة تحكم المدير العام",
  },
  {
    key: "quantity-engineer",
    label: "مهندس الكميات",
    email: process.env.TEST_QUANTITY_ENGINEER_EMAIL || "q1@test.com",
    password: process.env.TEST_QUANTITY_ENGINEER_PASSWORD || defaultPassword,
    path: "/quantity-engineer",
    waitText: "مهندس الكميات",
  },
  {
    key: "engineer",
    label: "المهندس",
    email: process.env.TEST_ENGINEER_EMAIL || "en1@test.com",
    password: process.env.TEST_ENGINEER_PASSWORD || defaultPassword,
    path: "/engineer",
    waitText: "نظام طلبات المواد",
  },
  {
    key: "supervisor",
    label: "مشرف/مشروع",
    email: process.env.TEST_SUPERVISOR_EMAIL || "a223@test.com",
    password: process.env.TEST_SUPERVISOR_PASSWORD || defaultPassword,
    path: "/supervisor",
    waitText: "نظام طلبات المواد",
  },
  {
    key: "printer",
    label: "طباعة",
    email: process.env.TEST_PRINTER_EMAIL || "p1@test.com",
    password: process.env.TEST_PRINTER_PASSWORD || defaultPassword,
    path: "/printer",
    waitText: "نظام طلبات المواد",
  },
  {
    key: "delivery-tracker",
    label: "متتبع التسليم",
    email: process.env.TEST_DELIVERY_TRACKER_EMAIL || "d1@test.com",
    password: process.env.TEST_DELIVERY_TRACKER_PASSWORD || defaultPassword,
    path: "/delivery-tracker",
    waitText: "نظام متابعة التوريد",
  },
];

const buttonSelector = "button, [role=\"button\"], a[role=\"button\"]";

function ensureOutputDir() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
}

function loadButtonLog() {
  if (!fs.existsSync(BUTTON_LOG_PATH)) {
    return [];
  }
  try {
    return JSON.parse(fs.readFileSync(BUTTON_LOG_PATH, "utf-8"));
  } catch (error) {
    return [];
  }
}

function saveButtonLog(entries) {
  fs.writeFileSync(BUTTON_LOG_PATH, JSON.stringify(entries, null, 2));
}

async function getButtonsSnapshot(page) {
  return page.evaluate((selector) => {
    const nodes = Array.from(document.querySelectorAll(selector));
    return nodes.map((node, index) => {
      const text = (node.innerText || node.textContent || "").trim();
      const ariaLabel = (node.getAttribute("aria-label") || "").trim();
      const title = (node.getAttribute("title") || "").trim();
      const testId = (node.getAttribute("data-testid") || "").trim();
      const id = (node.getAttribute("id") || "").trim();
      const label =
        text ||
        ariaLabel ||
        title ||
        (testId ? `data-testid:${testId}` : "") ||
        (id ? `id:${id}` : "") ||
        "بدون_نص";
      const style = window.getComputedStyle(node);
      const visible =
        style.visibility !== "hidden" &&
        style.display !== "none" &&
        node.getClientRects().length > 0;
      const disabled =
        node.hasAttribute("disabled") ||
        node.getAttribute("aria-disabled") === "true";
      return {
        index,
        label,
        visible,
        enabled: visible && !disabled,
      };
    });
  }, buttonSelector);
}

async function scanButtons(page, contextLabel, state) {
  const results = [];
  const snapshot = await getButtonsSnapshot(page);
  const buttons = page.locator(buttonSelector);

  for (const item of snapshot) {
    let clickable = null;
    let error = null;

    if (item.visible && item.enabled) {
      if (state.trialCount >= MAX_TRIAL_CLICKS) {
        error = "trial_skipped_limit";
      } else {
        try {
          await buttons.nth(item.index).click({ trial: true, timeout: 2000 });
          clickable = true;
          state.trialCount += 1;
        } catch (err) {
          error = err?.message || String(err);
          clickable = false;
        }
      }
    }

    results.push({
      context: contextLabel,
      label: item.label,
      visible: item.visible,
      enabled: item.enabled,
      clickable,
      error,
    });
  }

  return results;
}

async function scanTabsAndButtons(page, roleLabel, state) {
  const allResults = [];
  const tabs = page.locator("[role=\"tab\"]");
  const tabCount = await tabs.count();

  if (tabCount === 0) {
    return scanButtons(page, `${roleLabel}::default`, state);
  }

  for (let i = 0; i < tabCount; i += 1) {
    const tab = tabs.nth(i);
    const tabLabel = (await tab.innerText().catch(() => ""))?.trim() || `tab-${i + 1}`;
    try {
      await tab.click({ timeout: 5000 });
      await page.waitForTimeout(500);
    } catch (error) {
      allResults.push({
        context: `${roleLabel}::tab`,
        label: tabLabel,
        visible: await tab.isVisible().catch(() => false),
        enabled: await tab.isEnabled().catch(() => false),
        clickable: false,
        error: error?.message || String(error),
      });
      continue;
    }

    const tabResults = await scanButtons(page, `${roleLabel}::${tabLabel}`, state);
    allResults.push(...tabResults);
  }

  return allResults;
}

async function dismissToasts(page) {
  const closeButtons = page.locator('button[aria-label="Close toast"]');
  const count = await closeButtons.count();
  for (let i = 0; i < count; i += 1) {
    try {
      await closeButtons.nth(i).click({ timeout: 1000 });
    } catch (error) {
      continue;
    }
  }
}

test.describe("Full UI button scan per role", () => {
  for (const role of roles) {
    test(`${role.label} dashboard buttons`, async ({ page }) => {
      ensureOutputDir();

      await page.goto("/login", { waitUntil: "networkidle" });
      await page.getByTestId("login-email-input").fill(role.email);
      await page.getByTestId("login-password-input").fill(role.password);
      await page.getByTestId("login-submit-btn").click();

      await page.waitForURL(new RegExp(`${role.path}.*`), { timeout: 30000 });
      if (role.waitText) {
        await page.getByRole("heading", { name: role.waitText }).waitFor({ timeout: 30000 });
      }
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      await dismissToasts(page);

      const screenshotPath = path.join(OUTPUT_DIR, `ui-${role.key}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });

      const scanState = { trialCount: 0 };
      const scanResults = await scanTabsAndButtons(page, role.label, scanState);
      const existing = loadButtonLog();
      saveButtonLog([...existing, ...scanResults]);

      const video = page.video();
      await page.close();
      if (video) {
        const videoPath = await video.path();
        const targetPath = path.join(OUTPUT_DIR, `ui-${role.key}.webm`);
        fs.copyFileSync(videoPath, targetPath);
      }
    });
  }
});
