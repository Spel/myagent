const fs = require('fs');

const changelog = {
  data: {
    title: "BenchGen Beta Roadmap Update (v0.2.0-preview)",
    slug: "changelog-benchgen-beta-roadmap-update-v0-2-0-preview",
    version: "0.2.0-preview",
    tag: "improved",
    summary: "A sneak peek at v0.2.0: detailing Digital-Twin sandboxes, domain filtering for Odoo/SAP, and zero-click fine-tuning pipelines.",
    content: `## 🌟 Sneak Peek: BenchGen v0.2.0

We are pushing hard toward our beta release! This preview outlines the major pillars of the upcoming **BenchGen v0.2.0** update:

### 1. Digital-Twin Sandboxes
* Simulated ERP and CRM systems.
* Validate agent decisions under multi-step business transactional stress.

### 2. Specialized Domain Filtering
* Out-of-the-box scoring matrices for critical business suites (Odoo, SAP, Salesforce).
* Enhanced accuracy tracking on structured workflows.

### 3. Sovereign GPU Training Pipelines
* One-click dataset push from evaluated trajectory groups to fine-tuning pipelines.
`,
    publishedAt: new Date().toISOString()
  }
};

console.log(JSON.stringify(changelog, null, 2));
