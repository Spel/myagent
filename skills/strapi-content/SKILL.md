# Strapi Content Management Skill

This skill provides a standardized, reliable procedure for interacting with Strapi's \`/api/articles\` and \`/api/changelog-entries\` endpoints using secure Bearer authentication. It covers retrieving, creating, updating, and synchronizing markdown pages and changelog updates with Strapi.

---

## 📋 Prerequisites & Credentials

Ensure the following environment variables are configured in the workspace root \`.env\` file (\`chmod 600\`):
- **STRAPI_BASE_URL:** \`https://admin.benchgen.com/\` (Default)
- **STRAPI_API_KEY:** Secure token with access to read/write/update \`api::article.article\` and \`api::changelog-entry.changelog-entry\` content types.

---

## 🛠️ Step-by-Step Procedures

### 1. Retrieving Entries (List / Search)
To fetch current entries, paginate, or search by filters (e.g. by \`slug\`).

**A. Articles Endpoint:** \`/api/articles\`  
**B. Changelog Entries Endpoint:** \`/api/changelog-entries\`

**Example: Search Changelog by Version or Slug (using curl)**
\`\`\`bash
curl -s -k -H \"Authorization: Bearer <STRAPI_API_KEY>\" \
  \"https://admin.benchgen.com/api/changelog-entries?filters[slug][\$eq]=<slug>&populate=*\"
\`\`\`

**Using Node.js for complex responses:**
\`\`\`javascript
const response = await fetch(\"https://admin.benchgen.com/api/changelog-entries?pagination[pageSize]=100\", {
  headers: {
    \"Authorization\": \`Bearer \${process.env.STRAPI_API_KEY}\`
  }
});
const result = await response.json();
console.log(result.data.map(item => ({ id: item.id, documentId: item.documentId, title: item.title, slug: item.slug })));
\`\`\`

---

### 2. Fetching a Single Entry
To retrieve a detailed payload including markdown content.

**Method:** \`GET\`  
**Endpoint:** \`/api/<endpoint>?filters[slug][\$eq]=<slug>\` (or by direct documentId: \`/api/<endpoint>/<documentId>\`)

---

### 3. Creating a New Entry
When publishing new content to Strapi.

**A. New Article Format:**
\`\`\`json
{
  \"data\": {
    \"title\": \"My New Article\",
    \"slug\": \"my-new-article\",
    \"content\": \"# My New Article\nContent...\",
    \"excerpt\": \"Short excerpt description.\",
    \"publishedAt\": \"2026-06-15T19:00:00.000Z\"
  }
}
\`\`\`

**B. New Changelog Entry Format:**
\`\`\`json
{
  \"data\": {
    \"title\": \"BenchGen Pre-Launch Alpha (v0.1.0)\",
    \"slug\": \"changelog-benchgen-pre-launch-alpha-v0-1-0\",
    \"version\": \"0.1.0\",
    \"tag\": \"new\",
    \"summary\": \"Short summary of release features.\",
    \"content\": \"# Release notes in markdown format...\",
    \"publishedAt\": \"2026-06-15T20:00:00.000Z\"
  }
}
\`\`\`

---

### 4. Updating an Existing Entry
When local files change and need to be synced back to Strapi.

**Method:** \`PUT\`  
**Endpoint:** \`/api/<endpoint>/<documentId>\`

> **Note:** Always perform a \`GET\` with filters on the slug first to obtain the precise \`documentId\` of the target entry before running the update request.

---

## ⚠️ Error Handling & Safety

1. **Unauthorized / Forbidden (401/403):** Double-check your Bearer token scope. Ensure it covers both \`api::article\` and \`api::changelog-entry\` in Strapi's permissions dashboard.
2. **Slug Conflicts:** Before creating (\`POST\`) any entry, run a \`GET\` check on the slug. If an entry already exists, perform a \`PUT\` update on its \`documentId\` instead to prevent duplication.
3. **Double Quotes & Formatting:** Properly escape JSON payload strings when compiling markdown contents to avoid parse errors. Prefer reading the file stream and JSON-encoding dynamically via Node.js.
