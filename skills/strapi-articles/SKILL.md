# Strapi Articles Management Skill

This skill provides a standardized, reliable procedure for interacting with Strapi's `/api/articles` endpoint using secure Bearer authentication. It covers retrieving, creating, updating, and synchronizing markdown pages with Strapi.

---

## 📋 Prerequisites & Credentials

Ensure the following environment variables are configured or provided before execution:
- **Strapi Base URL:** `https://admin.benchgen.com/` (Default)
- **Strapi API Key:** Secure token with access to read/write/update `api::article.article` content types.

---

## 🛠️ Step-by-Step Procedures

### 1. Retrieving Articles (List / Search)
To fetch the current list of articles, paginate, or search by fields.

**Method:** `GET`
**Endpoint:** `/api/articles`

**Retrieve with pagination and filtering by slug:**
```bash
curl -s -k -H "Authorization: Bearer <STRAPI_API_KEY>" \
  "https://admin.benchgen.com/api/articles?filters[slug][$eq]=<slug>&populate=*"
```

**Using Node.js for complex responses:**
```javascript
const response = await fetch("https://admin.benchgen.com/api/articles?pagination[pageSize]=100", {
  headers: {
    "Authorization": `Bearer ${process.env.STRAPI_API_KEY}`
  }
});
const result = await response.json();
console.log(result.data.map(item => ({ id: item.id, title: item.title, slug: item.slug })));
```

---

### 2. Fetching a Single Article
To retrieve a detailed article payload including markdown content.

**Method:** `GET`
**Endpoint:** `/api/articles?filters[slug][$eq]=<slug>` (or by `id` directly: `/api/articles/<id>`)

**Verify and Extract Content:**
Always verify that the document matches the requested slug before performing any parsing or updates.

---

### 3. Creating a New Article
When a new markdown page needs to be published to Strapi.

**Method:** `POST`
**Endpoint:** `/api/articles`
**Content-Type:** `application/json`

**Expected Payload Format:**
Strapi v5 expects the root payload containing attributes under `data`.
```json
{
  "data": {
    "title": "My New Article",
    "slug": "my-new-article",
    "content": "# My New Article
Content goes here...",
    "excerpt": "Short excerpt description.",
    "publishedAt": "2026-06-15T19:00:00.000Z"
  }
}
```

**Implementation Command:**
```bash
curl -s -k -X POST -H "Authorization: Bearer <STRAPI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"title\": \"<title>\", \"slug\": \"<slug>\", \"content\": \"<escaped_content>\"}}" \
  "https://admin.benchgen.com/api/articles"
```

---

### 4. Updating an Existing Article
When a local markdown file changes and needs to be synchronized/pushed to Strapi.

**Method:** `PUT`
**Endpoint:** `/api/articles/<documentId_or_id>`

> **Note:** Always perform a `GET` with filters on the slug first to obtain the precise `id` or `documentId` of the target entry before running the update request.

**Implementation Command:**
```bash
curl -s -k -X PUT -H "Authorization: Bearer <STRAPI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"content\": \"<escaped_updated_content>\"}}" \
  "https://admin.benchgen.com/api/articles/<id>"
```

---

## ⚠️ Error Handling & Safety

1. **Unauthorized / Forbidden (401/403):** Double-check that your `Authorization: Bearer <key>` header has no typos and is fully permitted to manage the `api::article` content type inside Strapi’s settings.
2. **Slug Conflicts:** Before posting a new article, search Strapi for any existing article matching the target `slug`. If one exists, execute a `PUT` update on the existing `id` rather than a duplicate `POST`.
3. **Escaping Content:** When compiling raw JSON body strings containing markdown, always ensure proper escaping of double quotes (`"`), newlines (`
`), and backslashes (`\`) to prevent JSON parse errors. If using a shell script, prefer reading from a file and generating the body structure via `node`.
