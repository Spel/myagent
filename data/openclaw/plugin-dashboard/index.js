// Company Brain Analysis Dashboard — OpenClaw Plugin Entry
// Registers an HTTP route that serves dist/index.html and adds a sidebar tab.
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default definePluginEntry({
  id: "company-brain-dashboard",
  name: "Company Brain — Analysis Dashboard",
  description: "Session analysis, bug tracker, task list, and user status",

  register(api) {
    // ── HTTP route: serve dist/index.html at the plugin root ──────────────
    // Accessible at: /__openclaw__/plugin/company-brain-dashboard/
    api.registerHttpRoute({
      method: "GET",
      path: "/",
      auth: "gateway",
      async handler(_req, res) {
        const htmlPath = join(__dirname, "dist", "index.html");
        try {
          const html = readFileSync(htmlPath, "utf-8");
          res.writeHead(200, {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-cache, no-store, must-revalidate",
          });
          res.end(html);
        } catch {
          res.writeHead(503, { "Content-Type": "text/plain" });
          res.end("Dashboard not yet built. Run build.py on the server.");
        }
      },
    });

    // ── Sidebar tab in the Control UI ─────────────────────────────────────
    api.session.controls.registerControlUiDescriptor({
      surface: "tab",
      id: "company-brain-dashboard",
      label: "Dashboard",
      description: "Company Brain analytics: sessions, bugs, tasks, users",
      icon: "chart-bar",
      group: "control",
      path: "/",
    });
  },
});
