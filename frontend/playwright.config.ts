import { defineConfig, devices } from "@playwright/test";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const scratch = path.join(root, ".e2e");
mkdirSync(scratch, { recursive: true });
const run = mkdtempSync(path.join(scratch, "run-"));
const database = path.join(run, "test.db");
copyFileSync(path.join(root, "data", "panataanph.db"), database);
const venvPython = path.join(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const python =
  process.env.PANATAANPH_TEST_PYTHON || (existsSync(venvPython) ? venvPython : "python");

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5174", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command: `"${python}" tests/browser_fixture.py && "${python}" -m uvicorn backend.main:app --app-dir src --host 127.0.0.1 --port 8100`,
      cwd: root,
      url: "http://127.0.0.1:8100/api/health",
      env: {
        PANATAANPH_DB_PATH: database,
        PANATAANPH_STORAGE_PATH: path.join(run, "storage"),
        PYTHONPATH: path.join(root, "src"),
        PANATAANPH_RATE_LIMIT: "false",
      },
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { PANATAANPH_API_TARGET: "http://127.0.0.1:8100" },
    },
  ],
});
