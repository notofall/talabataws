const { defineConfig } = require("@playwright/test");

const outputDir = process.env.PW_OUTPUT_DIR || "/opt/cursor/artifacts/playwright-results";

module.exports = defineConfig({
  testDir: __dirname,
  timeout: 360000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.UI_BASE_URL || "http://52.66.118.46:3000",
    headless: true,
    viewport: { width: 1365, height: 768 },
    video: "on",
  },
  outputDir,
});
