-- Company Brain Learning Loop — SQLite Schema
-- One file, backed up by brain-push.sh, queryable with any SQLite client.
-- Target: analysis.db (gitignored; regenerate with ingest.py)

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─── sessions ────────────────────────────────────────────────────────────────
-- One row per .jsonl file (active/reset/deleted all included)
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    source_file  TEXT NOT NULL,
    session_key  TEXT,
    user_id      TEXT,
    user_name    TEXT,
    topic        TEXT,
    status       TEXT,            -- active | reset | deleted
    started_at   INTEGER,         -- epoch ms
    ended_at     INTEGER,
    n_turns      INTEGER DEFAULT 0,
    n_user_turns INTEGER DEFAULT 0,
    n_asst_turns INTEGER DEFAULT 0,
    n_tool_calls INTEGER DEFAULT 0,
    n_errors     INTEGER DEFAULT 0,
    posts_published  INTEGER DEFAULT 0,
    posts_retried    INTEGER DEFAULT 0,
    gate1_pass   INTEGER DEFAULT 0,
    gate1_fail   INTEGER DEFAULT 0,
    enoent_count INTEGER DEFAULT 0,
    no_reply_count INTEGER DEFAULT 0,
    outcome      TEXT,            -- success | partial | failed | abandoned | unknown
    analyzed     INTEGER DEFAULT 0,
    ingested_at  INTEGER          -- epoch ms, when ingest.py processed this
);

-- ─── events ──────────────────────────────────────────────────────────────────
-- One row per turn / tool call. The granular table — everything derives from here.
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,   -- session_id + ":" + line_index
    session_id  TEXT NOT NULL REFERENCES sessions(session_id),
    user_id     TEXT,
    topic       TEXT,
    line_idx    INTEGER,
    ts          INTEGER,            -- epoch ms (from message timestamp)
    role        TEXT,               -- user | assistant | tool
    type        TEXT,               -- message | tool_call | tool_result | error | system
    tool_name   TEXT,               -- exec | image | read | write | li-post | li-auth | ...
    model       TEXT,               -- model name if available from trajectory
    content     TEXT,               -- text content (truncated to 1000 chars)
    content_len INTEGER,            -- full content length
    error       TEXT,               -- error string if any
    has_error   INTEGER DEFAULT 0,
    source_file TEXT
);

-- ─── signals ─────────────────────────────────────────────────────────────────
-- Extracted behavioral signals — the labeled dataset.
-- These are the events that carry learning value.
CREATE TABLE IF NOT EXISTS signals (
    signal_id   TEXT PRIMARY KEY,   -- uuid
    session_id  TEXT NOT NULL REFERENCES sessions(session_id),
    event_id    TEXT REFERENCES events(event_id),
    user_id     TEXT,
    topic       TEXT,
    ts          INTEGER,
    signal_type TEXT NOT NULL,      -- see signal taxonomy below
    value       REAL DEFAULT 1.0,   -- magnitude (1.0 = present, 0.0 = absent)
    evidence    TEXT,               -- snippet that triggered the signal
    created_at  INTEGER
);

-- Signal taxonomy (signal_type values):
--   publish_success     — li-post.sh returned OK:
--   publish_fail        — li-post.sh returned NO_TOKEN / TOKEN_EXPIRED / ERROR
--   publish_retry       — ≥2 li-post.sh calls in same session (same content)
--   draft_accepted      — user explicitly approved a draft ("публікуй", "publish", "yes")
--   draft_rewritten     — user provided edited version after agent draft
--   gate1_pass          — GATE1=pass execution result
--   gate1_fail          — GATE1=fail execution result
--   user_approved       — IS_APPROVED=true
--   user_not_approved   — IS_APPROVED=false
--   file_missing        — ENOENT error
--   search_offline      — web_search disabled / offline
--   duplicate_response  — NO_REPLY sentinel detected
--   token_expired       — LinkedIn token expired during session
--   self_correction     — agent used "стоп", "щось не так", "let me check"
--   session_abandoned   — no user reply after agent question (last turn is assistant)
--   image_fail          — image tool or li-post image path failed
--   explicit_like       — user tapped 👍 button (future)
--   explicit_dislike    — user tapped 👎 button (future)

-- ─── learnings ───────────────────────────────────────────────────────────────
-- Our custom .learnings/ layer backed by SQL.
-- Mirror of .learnings/*.md — queryable and cross-session.
CREATE TABLE IF NOT EXISTS learnings (
    learning_id  TEXT PRIMARY KEY,  -- ERR/CORR/FEAT-YYYYMMDD-NNN
    type         TEXT,              -- error | correction | feature | pattern
    status       TEXT DEFAULT 'pending_review',  -- pending_review | reviewed | promoted | archived
    risk_tier    TEXT DEFAULT 'low',             -- low | medium | high
    created_at   TEXT,
    promoted_at  TEXT,
    user_ids     TEXT,              -- JSON array of affected users
    session_ids  TEXT,             -- JSON array of session IDs
    bug_id       TEXT,             -- link to bugs.json (e.g. "BUG-002")
    title        TEXT,
    summary      TEXT,
    root_cause   TEXT,
    proposed_rule TEXT,
    promoted_rule TEXT,            -- the actual text added to AGENTS.md / SKILL.md
    occurrence_count INTEGER DEFAULT 1,
    eval_required INTEGER DEFAULT 0,
    eval_passed   INTEGER,
    signal_type   TEXT            -- which signal triggered this learning
);

-- ─── eval_runs ───────────────────────────────────────────────────────────────
-- Evaluation history — score trend over time.
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id       TEXT PRIMARY KEY,
    run_at       INTEGER,          -- epoch ms
    trigger      TEXT,             -- manual | promotion_gate | scheduled
    n_tasks      INTEGER,
    score        REAL,             -- 0.0–1.0
    score_sem    REAL,             -- standard error of mean (Anthropic recommendation)
    by_scenario  TEXT,            -- JSON: {scenario: score}
    notes        TEXT
);

-- ─── ingest_state ────────────────────────────────────────────────────────────
-- Tracks which files have been processed (incremental ingestion).
CREATE TABLE IF NOT EXISTS ingest_state (
    file_path    TEXT PRIMARY KEY,
    mtime        REAL,            -- file modification time
    n_lines      INTEGER,
    ingested_at  INTEGER
);

-- ─── Useful views ─────────────────────────────────────────────────────────────

CREATE VIEW IF NOT EXISTS v_user_metrics AS
SELECT
    s.user_id,
    s.user_name,
    COUNT(DISTINCT s.session_id)                                        AS n_sessions,
    SUM(s.n_turns)                                                      AS total_turns,
    SUM(s.posts_published)                                              AS posts_published,
    SUM(s.posts_retried)                                                AS posts_retried,
    SUM(s.n_errors)                                                     AS total_errors,
    SUM(s.gate1_fail)                                                   AS gate1_fails,
    SUM(s.enoent_count)                                                 AS file_missing_count,
    SUM(s.no_reply_count)                                               AS duplicate_responses,
    ROUND(1.0 * SUM(s.posts_published) /
          NULLIF(SUM(s.posts_published) + SUM(s.posts_retried), 0), 3) AS first_try_publish_rate
FROM sessions s
WHERE s.user_id IS NOT NULL
GROUP BY s.user_id, s.user_name;

CREATE VIEW IF NOT EXISTS v_signal_counts AS
SELECT
    user_id,
    signal_type,
    COUNT(*)                      AS n,
    MIN(ts)                       AS first_seen,
    MAX(ts)                       AS last_seen,
    COUNT(DISTINCT session_id)    AS n_sessions
FROM signals
GROUP BY user_id, signal_type;

CREATE VIEW IF NOT EXISTS v_publish_success_rate AS
SELECT
    user_id,
    COUNT(CASE WHEN signal_type = 'publish_success' THEN 1 END) AS successes,
    COUNT(CASE WHEN signal_type = 'publish_fail'    THEN 1 END) AS failures,
    COUNT(CASE WHEN signal_type = 'publish_retry'   THEN 1 END) AS retries,
    ROUND(
        1.0 * COUNT(CASE WHEN signal_type = 'publish_success' THEN 1 END) /
        NULLIF(COUNT(CASE WHEN signal_type IN ('publish_success','publish_fail') THEN 1 END), 0),
    3) AS success_rate
FROM signals
WHERE signal_type IN ('publish_success','publish_fail','publish_retry')
GROUP BY user_id;
