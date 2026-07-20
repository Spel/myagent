#!/usr/bin/env python3
"""
Company Brain Learning Loop — Data Ingestion
=============================================
Reads session JSONL files from logs/sessions-raw/
Writes structured events + sessions + signals to learning-loop/analysis.db

Incremental: tracks processed files via the ingest_state table.
Safe to re-run: uses INSERT OR REPLACE and transaction batches.

Usage:
  python3 learning-loop/ingest.py              # incremental
  python3 learning-loop/ingest.py --full       # reprocess all files
  python3 learning-loop/ingest.py --stats      # print stats and exit
"""

import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT    = Path(__file__).parent.parent
SESSIONS_DIR = REPO_ROOT / 'logs' / 'sessions-raw'
DB_PATH      = REPO_ROOT / 'learning-loop' / 'analysis.db'
SCHEMA_PATH  = REPO_ROOT / 'learning-loop' / 'schema.sql'

# ─── Known user registry ──────────────────────────────────────────────────────
USERS = {
    '264468965': 'Andrii (Owner)',
    '373382939': 'Rudolf',
    '547748231': 'Catherine Miliutenko',
}

# ─── Signal detection patterns ────────────────────────────────────────────────
SIGNAL_RULES = [
    ('publish_success',    r'ok:\s*https://www\.linkedin\.com/feed/update/'),
    ('publish_fail',       r'no_token:|token_expired:|error \d{3}:.*linkedin'),
    ('gate1_fail',         r'gate1=fail'),
    ('gate1_pass',         r'gate1=pass'),
    ('user_approved',      r'is_approved=true'),
    ('user_not_approved',  r'is_approved=false'),
    ('file_missing',       r'enoent:'),
    ('search_offline',     r'web.?search.{0,20}(offline|disabled|no provider)'),
    ('duplicate_response', r'\bno_reply\b'),
    ('token_expired',      r'token.{0,15}expir'),
    ('self_correction',    r'(стоп,|щось не так|let me check|перевіряю:|something wrong)'),
    ('image_fail',         r'resolveMediaBufferPath|media.{0,20}does not resolve'),
]
SIGNAL_PATTERNS = [(t, re.compile(p, re.IGNORECASE)) for t, p in SIGNAL_RULES]

DRAFT_ACCEPT_WORDS = re.compile(
    r'\b(публікуй|опублікуй|publish|yes|go ahead|post it|send it|так|давай)\b',
    re.IGNORECASE
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ts_to_ms(ts):
    """Convert ISO timestamp string or int/float to epoch ms."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return int(ts) if ts > 1e10 else int(ts * 1000)
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def extract_text(content):
    """Flatten message content to plain text (handles str or list-of-parts)."""
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get('type') == 'text':
                    parts.append(part.get('text', ''))
                elif part.get('type') == 'tool_result':
                    inner = part.get('content', '')
                    parts.append(extract_text(inner))
                elif part.get('type') == 'tool_use':
                    inp = part.get('input', {})
                    parts.append(f"[TOOL:{part.get('name','')}] {json.dumps(inp)[:200]}")
        return '\n'.join(filter(None, parts))
    return str(content)


def extract_tool_name(content, role):
    """Try to identify the tool name from a tool call or result."""
    if not isinstance(content, list):
        return None
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get('type') == 'tool_use':
            return part.get('name')
        if part.get('type') == 'tool_result':
            # Look for the tool ID in parent message
            return None
    return None


def detect_signals(text, role, session_id, event_id, user_id, topic, ts):
    """Return list of signal dicts for a given event text."""
    found = []
    low = text.lower()
    for sig_type, pattern in SIGNAL_PATTERNS:
        if pattern.search(low):
            # Avoid false positive: gate1=fail from skill code (not execution)
            if sig_type in ('gate1_fail', 'gate1_pass'):
                # Only count if it's a tool result, not assistant reading a skill
                if role not in ('tool', 'toolResult'):
                    continue
            found.append({
                'signal_id':   str(uuid.uuid4()),
                'session_id':  session_id,
                'event_id':    event_id,
                'user_id':     user_id,
                'topic':       topic,
                'ts':          ts,
                'signal_type': sig_type,
                'value':       1.0,
                'evidence':    text[:200],
                'created_at':  int(time.time() * 1000),
            })
    # Draft accepted: user message with acceptance phrase following an assistant turn
    if role == 'user' and DRAFT_ACCEPT_WORDS.search(text):
        found.append({
            'signal_id':   str(uuid.uuid4()),
            'session_id':  session_id,
            'event_id':    event_id,
            'user_id':     user_id,
            'topic':       topic,
            'ts':          ts,
            'signal_type': 'draft_accepted',
            'value':       1.0,
            'evidence':    text[:200],
            'created_at':  int(time.time() * 1000),
        })
    return found


def guess_user(text, known_users):
    """Heuristic: find a known user UID in raw line text."""
    for uid in known_users:
        if uid in text:
            return uid
    return None


def session_meta_from_filename(fname):
    """Derive topic and status from JSONL filename."""
    status = 'active'
    topic = None
    if '.deleted.' in fname:
        status = 'deleted'
    elif '.reset.' in fname:
        status = 'reset'
    m = re.search(r'topic-(\d+)', fname)
    if m:
        topic = m.group(1)
    return status, topic


# ─── Core ingestion ───────────────────────────────────────────────────────────

def parse_session_file(fpath, session_id, user_id, topic, status, sessions_index):
    """Parse a single session JSONL file. Returns (session_row, events[], signals[])."""
    events = []
    signals = []
    started_at = ended_at = None
    n_turns = n_user = n_asst = n_tool = n_errors = 0
    posts_published = posts_retried = gate1_pass = gate1_fail = 0
    enoent_count = no_reply_count = 0

    publish_bodies_seen = set()

    try:
        lines = fpath.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception as e:
        print(f"  warn: can't read {fpath.name}: {e}")
        return None, [], []

    for i, raw_line in enumerate(lines):
        if not raw_line.strip():
            continue
        try:
            obj = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        # ── Extract message from various wrapper formats ─────────────────────
        msg = None
        if isinstance(obj, dict):
            if 'message' in obj and isinstance(obj['message'], dict):
                msg = obj['message']
            elif obj.get('type') == 'message' and 'role' in obj:
                msg = obj
            elif 'role' in obj:
                msg = obj

        if not msg:
            continue

        role    = msg.get('role') or ''
        content_raw = msg.get('content', '')
        ts_str  = msg.get('timestamp') or obj.get('timestamp')
        ts_ms   = ts_to_ms(ts_str)
        text    = extract_text(content_raw)

        if ts_ms:
            if started_at is None or ts_ms < started_at:
                started_at = ts_ms
            if ended_at is None or ts_ms > ended_at:
                ended_at = ts_ms

        # ── Try to resolve user_id from content ─────────────────────────────
        if not user_id:
            found_uid = guess_user(raw_line, USERS)
            if found_uid:
                user_id = found_uid

        # ── Tool name ────────────────────────────────────────────────────────
        tool_name = extract_tool_name(content_raw if isinstance(content_raw, list) else [], role)
        # Fallback: look for tool references in text
        if not tool_name and role in ('tool', 'toolResult'):
            for tname in ('li-post.sh', 'li-auth.sh', 'exec', 'read', 'write', 'image', 'fetch'):
                if tname in text:
                    tool_name = tname
                    break

        # ── Counters ─────────────────────────────────────────────────────────
        has_err = 0
        n_turns += 1
        if role == 'user':
            n_user += 1
        elif role == 'assistant':
            n_asst += 1
            if 'NO_REPLY' in text:
                no_reply_count += 1
        elif role in ('tool', 'toolResult'):
            n_tool += 1

        low = text.lower()
        if 'enoent' in low:
            enoent_count += 1
        if '"status":"error"' in raw_line.lower() or 'error' in (msg.get('type','') or '').lower():
            n_errors += 1
            has_err = 1

        # Publish tracking
        if 'ok: https://www.linkedin.com/feed/update/' in low:
            body_snippet = text[text.lower().find('ok:'):text.lower().find('ok:')+100]
            if body_snippet in publish_bodies_seen:
                posts_retried += 1
            else:
                publish_bodies_seen.add(body_snippet)
                posts_published += 1

        # Gate1 tracking (tool results only)
        if role in ('tool', 'toolResult'):
            if 'gate1=pass' in low:
                gate1_pass += 1
            if 'gate1=fail' in low:
                gate1_fail += 1

        # ── Build event row ──────────────────────────────────────────────────
        event_id = f"{session_id}:{i}"
        event = {
            'event_id':    event_id,
            'session_id':  session_id,
            'user_id':     user_id,
            'topic':       topic,
            'line_idx':    i,
            'ts':          ts_ms,
            'role':        role,
            'type':        'message',
            'tool_name':   tool_name,
            'model':       None,
            'content':     text[:1000],
            'content_len': len(text),
            'error':       None,
            'has_error':   has_err,
            'source_file': fpath.name,
        }
        events.append(event)

        # ── Extract signals ──────────────────────────────────────────────────
        sigs = detect_signals(text, role, session_id, event_id, user_id, topic, ts_ms)
        signals.extend(sigs)

    # ── Determine session outcome ─────────────────────────────────────────────
    outcome = 'unknown'
    if posts_published > 0 and n_errors == 0:
        outcome = 'success'
    elif posts_published > 0:
        outcome = 'partial'
    elif n_errors > 0 and n_user > 0:
        outcome = 'failed'
    elif n_turns > 0 and n_user == 0:
        outcome = 'system'
    elif n_turns > 0:
        outcome = 'abandoned'

    session_row = {
        'session_id':      session_id,
        'source_file':     fpath.name,
        'session_key':     sessions_index.get(session_id, {}).get('key', ''),
        'user_id':         user_id,
        'user_name':       USERS.get(user_id) if user_id else None,
        'topic':           topic,
        'status':          status,
        'started_at':      started_at,
        'ended_at':        ended_at,
        'n_turns':         n_turns,
        'n_user_turns':    n_user,
        'n_asst_turns':    n_asst,
        'n_tool_calls':    n_tool,
        'n_errors':        n_errors,
        'posts_published': posts_published,
        'posts_retried':   posts_retried,
        'gate1_pass':      gate1_pass,
        'gate1_fail':      gate1_fail,
        'enoent_count':    enoent_count,
        'no_reply_count':  no_reply_count,
        'outcome':         outcome,
        'analyzed':        0,
        'ingested_at':     int(time.time() * 1000),
    }
    return session_row, events, signals


# ─── Database helpers ─────────────────────────────────────────────────────────

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    conn.executescript(schema)
    conn.commit()
    return conn


def file_needs_ingest(conn, fpath):
    mtime = fpath.stat().st_mtime
    row = conn.execute(
        'SELECT mtime FROM ingest_state WHERE file_path = ?', (str(fpath),)
    ).fetchone()
    return row is None or row['mtime'] != mtime


def mark_ingested(conn, fpath, n_lines):
    conn.execute(
        'INSERT OR REPLACE INTO ingest_state (file_path, mtime, n_lines, ingested_at) VALUES (?,?,?,?)',
        (str(fpath), fpath.stat().st_mtime, n_lines, int(time.time() * 1000))
    )


def insert_batch(conn, table, rows, cols):
    if not rows:
        return
    placeholders = ','.join(['?'] * len(cols))
    sql = f'INSERT OR REPLACE INTO {table} ({",".join(cols)}) VALUES ({placeholders})'
    conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])


# ─── Sessions index ───────────────────────────────────────────────────────────

def load_sessions_index():
    """Build uuid → {key, ...} map from sessions.json."""
    idx_path = SESSIONS_DIR / 'sessions.json'
    if not idx_path.exists():
        return {}
    try:
        raw = json.loads(idx_path.read_text(encoding='utf-8'))
        result = {}
        for key, val in raw.items():
            sid = val.get('sessionId', '')
            if sid:
                result[sid] = {'key': key, **val}
        return result
    except Exception:
        return {}


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    full_reprocess = '--full' in sys.argv
    stats_only     = '--stats' in sys.argv

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = init_db(DB_PATH)

    if stats_only:
        print_stats(conn)
        conn.close()
        return

    sessions_index = load_sessions_index()

    # Collect all processable JSONL files
    all_files = [
        f for f in sorted(SESSIONS_DIR.iterdir())
        if f.suffix == '.jsonl' or '.jsonl.reset.' in f.name
        if '.trajectory.' not in f.name
        if '.trajectory-path.' not in f.name
        if f.name != 'sessions.json'
    ]

    to_process = [f for f in all_files if full_reprocess or file_needs_ingest(conn, f)]
    print(f"Ingesting {len(to_process)}/{len(all_files)} files → {DB_PATH.name}")

    total_events = total_signals = 0

    for fpath in to_process:
        fname = fpath.name
        uuid_match = re.match(r'([0-9a-f-]{36})', fname)
        if not uuid_match:
            continue
        session_id = uuid_match.group(1)

        status, topic = session_meta_from_filename(fname)

        # Try to get user_id from known sessions in sessions.json or from analysis-state
        user_id = None
        analysis_state_path = REPO_ROOT / 'logs' / 'analysis' / 'analysis-state.json'
        if analysis_state_path.exists():
            try:
                state = json.loads(analysis_state_path.read_text())
                if fname in state:
                    user_id = state[fname].get('user_id')
            except Exception:
                pass

        session_row, events, signals = parse_session_file(
            fpath, session_id, user_id, topic, status, sessions_index
        )
        if session_row is None:
            continue

        with conn:
            # Sessions
            insert_batch(conn, 'sessions', [session_row], list(session_row.keys()))
            # Events
            if events:
                insert_batch(conn, 'events', events, list(events[0].keys()))
            # Signals
            if signals:
                insert_batch(conn, 'signals', signals, list(signals[0].keys()))
            mark_ingested(conn, fpath, len(events))

        total_events  += len(events)
        total_signals += len(signals)
        print(f"  {status:8} {topic or '-':6} {len(events):4}ev {len(signals):3}sig  {fname[:55]}")

    conn.close()
    print(f"\nDone. {len(to_process)} files → {total_events} events, {total_signals} signals")
    if to_process:
        print(f"DB: {DB_PATH}  ({DB_PATH.stat().st_size // 1024}KB)")


def print_stats(conn):
    print("=== analysis.db stats ===\n")
    for row in conn.execute('SELECT * FROM v_user_metrics ORDER BY posts_published DESC'):
        print(f"  {row['user_name'] or row['user_id']:25} | sessions:{row['n_sessions']:3} "
              f"| posts:{row['posts_published']:3} | errors:{row['total_errors']:3} "
              f"| gate1_fail:{row['gate1_fails']:3} | enoent:{row['file_missing_count']:3}")
    print()
    print("  Signal counts:")
    for row in conn.execute(
        'SELECT signal_type, COUNT(*) n, COUNT(DISTINCT user_id) users '
        'FROM signals GROUP BY signal_type ORDER BY n DESC'
    ):
        print(f"    {row['signal_type']:30} {row['n']:5}x  ({row['users']} users)")
    print()
    print("  Session outcomes:")
    for row in conn.execute(
        'SELECT outcome, COUNT(*) n FROM sessions GROUP BY outcome ORDER BY n DESC'
    ):
        outcome = row['outcome'] or 'unknown'
        print(f"    {outcome:15} {row['n']}")


if __name__ == '__main__':
    main()
