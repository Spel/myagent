#!/usr/bin/env python3
"""
Company Brain Learning Loop — Signal Extraction & Metrics
==========================================================
Reads events from analysis.db (populated by ingest.py)
Writes enriched signals and computes per-user metrics.

Also promotes high-frequency signals to learnings table entries.

Usage:
  python3 learning-loop/signal-extract.py          # process new events
  python3 learning-loop/signal-extract.py --report # print full report
"""

import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DB_PATH   = REPO_ROOT / 'learning-loop' / 'analysis.db'

# ─── Config ──────────────────────────────────────────────────────────────────
# How many signal occurrences before we promote to a learning entry
PROMOTE_THRESHOLD = 3

# Minimum sessions for cross-user pattern detection
CROSS_USER_THRESHOLD = 2


# ─── Sequential pattern detection ────────────────────────────────────────────
# These require looking at consecutive events within a session.

def detect_sequential_patterns(conn):
    """
    Detect patterns that require looking at event sequences:
    - draft_accepted: user short reply after long assistant turn
    - draft_rewritten: user long reply after long assistant turn
    - publish_retry: multiple publish signals in same session
    - session_abandoned: last turn is assistant, no follow-up
    """
    new_signals = []
    now_ms = int(time.time() * 1000)

    sessions = conn.execute(
        'SELECT session_id, user_id, topic FROM sessions WHERE n_turns > 1'
    ).fetchall()

    for sess in sessions:
        sid = sess['session_id']
        uid = sess['user_id']
        topic = sess['topic']

        events = conn.execute(
            'SELECT event_id, role, content, content_len, ts FROM events '
            'WHERE session_id = ? ORDER BY line_idx',
            (sid,)
        ).fetchall()

        # Detect publish retries within session
        pub_sigs = conn.execute(
            "SELECT signal_id FROM signals WHERE session_id = ? AND signal_type = 'publish_success'",
            (sid,)
        ).fetchall()
        if len(pub_sigs) > 1:
            # Check if we already have this signal
            existing = conn.execute(
                "SELECT 1 FROM signals WHERE session_id = ? AND signal_type = 'publish_retry'", (sid,)
            ).fetchone()
            if not existing:
                new_signals.append({
                    'signal_id':   str(uuid.uuid4()),
                    'session_id':  sid,
                    'event_id':    None,
                    'user_id':     uid,
                    'topic':       topic,
                    'ts':          now_ms,
                    'signal_type': 'publish_retry',
                    'value':       float(len(pub_sigs)),
                    'evidence':    f"{len(pub_sigs)} publish_success signals in one session",
                    'created_at':  now_ms,
                })

        # Detect session abandoned (last turn is assistant)
        if events:
            last = events[-1]
            if last['role'] == 'assistant':
                existing = conn.execute(
                    "SELECT 1 FROM signals WHERE session_id = ? AND signal_type = 'session_abandoned'",
                    (sid,)
                ).fetchone()
                if not existing:
                    new_signals.append({
                        'signal_id':   str(uuid.uuid4()),
                        'session_id':  sid,
                        'event_id':    last['event_id'],
                        'user_id':     uid,
                        'topic':       topic,
                        'ts':          last['ts'],
                        'signal_type': 'session_abandoned',
                        'value':       1.0,
                        'evidence':    (last['content'] or '')[:200],
                        'created_at':  now_ms,
                    })

        # Detect draft_accepted / draft_rewritten sequences
        for j in range(1, len(events)):
            prev = events[j - 1]
            curr = events[j]
            if prev['role'] == 'assistant' and curr['role'] == 'user':
                prev_len = prev['content_len'] or 0
                curr_len = curr['content_len'] or 0
                curr_text = curr['content'] or ''

                # Long assistant message followed by short user acceptance
                if prev_len > 200 and curr_len < 60:
                    import re
                    accept_pat = re.compile(
                        r'\b(публікуй|опублікуй|publish|yes|go ahead|post it|send it|так|давай|ок|ok|добре)\b',
                        re.IGNORECASE
                    )
                    if accept_pat.search(curr_text):
                        existing = conn.execute(
                            "SELECT 1 FROM signals WHERE event_id = ? AND signal_type = 'draft_accepted'",
                            (curr['event_id'],)
                        ).fetchone()
                        if not existing:
                            new_signals.append({
                                'signal_id':   str(uuid.uuid4()),
                                'session_id':  sid,
                                'event_id':    curr['event_id'],
                                'user_id':     uid,
                                'topic':       topic,
                                'ts':          curr['ts'],
                                'signal_type': 'draft_accepted',
                                'value':       1.0,
                                'evidence':    curr_text[:200],
                                'created_at':  now_ms,
                            })

                # Long user reply after long assistant = rewrite
                if prev_len > 200 and curr_len > 150:
                    existing = conn.execute(
                        "SELECT 1 FROM signals WHERE event_id = ? AND signal_type = 'draft_rewritten'",
                        (curr['event_id'],)
                    ).fetchone()
                    if not existing:
                        new_signals.append({
                            'signal_id':   str(uuid.uuid4()),
                            'session_id':  sid,
                            'event_id':    curr['event_id'],
                            'user_id':     uid,
                            'topic':       topic,
                            'ts':          curr['ts'],
                            'signal_type': 'draft_rewritten',
                            'value':       1.0,
                            'evidence':    curr_text[:200],
                            'created_at':  now_ms,
                        })

    return new_signals


# ─── Learning promotion ───────────────────────────────────────────────────────

LEARNING_TEMPLATES = {
    'publish_fail': {
        'type':         'error',
        'risk_tier':    'high',
        'title':        'LinkedIn publish fails with NO_TOKEN',
        'summary':      'li-post.sh returns NO_TOKEN despite user having a valid token. '
                        'Root cause: TELEGRAM_USER_ID not exported to subprocess environment.',
        'root_cause':   'TELEGRAM_USER_ID env var is set in the session context but not '
                        'inherited by bash subprocess running li-post.sh. '
                        'jq -r \'.[$u]\' gets an empty string for $u.',
        'proposed_rule': 'Always validate that TELEGRAM_USER_ID is non-empty before '
                         'calling li-post.sh. Add: [ -z "$TELEGRAM_USER_ID" ] && { echo "ERROR: TELEGRAM_USER_ID empty"; exit 1; }',
        'eval_required': 1,
    },
    'file_missing': {
        'type':         'error',
        'risk_tier':    'medium',
        'title':        'Required file missing (ENOENT) during session',
        'summary':      'Agent tries to read strategy.md, profile.md or content-calendar.md '
                        'that does not exist, causing skill failure or generic responses.',
        'root_cause':   'Files created during session but not committed to git. '
                        'On pod restart (git pull), local files are wiped.',
        'proposed_rule': 'Before using any per-user file, check existence and create from '
                         'template if missing. Never rely on file being present between sessions.',
        'eval_required': 0,
    },
    'gate1_fail': {
        'type':         'error',
        'risk_tier':    'high',
        'title':        'LinkedIn auth token missing or expired (GATE1 fail)',
        'summary':      'User is blocked from publishing because their LinkedIn OAuth token '
                        'is absent or expired. refresh_token is empty so no auto-renewal.',
        'root_cause':   'LinkedIn access tokens expire ~60 days. refresh_token was empty '
                        'at initial OAuth, so no silent renewal is possible.',
        'proposed_rule': 'Track token expiry date. Proactively warn user 7 days before '
                         'expiry with a re-auth link. Do not wait for GATE1=fail.',
        'eval_required': 0,
    },
    'duplicate_response': {
        'type':         'error',
        'risk_tier':    'medium',
        'title':        'NO_REPLY ghost messages causing duplicate sends',
        'summary':      'Agent sends a response, receives NO_REPLY sentinel, resends. '
                        'User sees duplicate messages.',
        'root_cause':   'Delivery confirmation race condition in OpenClaw Telegram transport. '
                        'First message actually delivered but confirmation delayed.',
        'proposed_rule': 'On NO_REPLY sentinel: log once and do NOT resend. '
                         'The delivery likely succeeded — resending creates duplicates.',
        'eval_required': 0,
    },
    'search_offline': {
        'type':         'error',
        'risk_tier':    'low',
        'title':        'Web search unavailable (missing API key)',
        'summary':      'web_search tool returns "offline" or "disabled" — ZEROENTROPY_API_KEY not set.',
        'root_cause':   'ZEROENTROPY_API_KEY env var missing from pod deployment.',
        'proposed_rule': 'When web_search is unavailable, say so explicitly and offer to '
                         'proceed without web context rather than silently omitting research.',
        'eval_required': 0,
    },
    'session_abandoned': {
        'type':         'pattern',
        'risk_tier':    'low',
        'title':        'Sessions ending with unanswered agent question',
        'summary':      'A significant portion of sessions end with an assistant turn '
                        '(question or draft) that the user never replies to.',
        'root_cause':   'Session resets wipe context; user has to re-explain each time. '
                        'Friction causes abandonment.',
        'proposed_rule': 'When a session resumes after a gap, offer a 1-line recap: '
                         '"Last time we were working on X. Continue?"',
        'eval_required': 0,
    },
    'publish_retry': {
        'type':         'pattern',
        'risk_tier':    'medium',
        'title':        'Multiple publish attempts in one session',
        'summary':      'Agent publishes the same or similar post more than once in a session, '
                        'creating duplicate LinkedIn posts.',
        'root_cause':   'Agent does not track published posts within session; '
                        'user confirmation flow retries after partial failure.',
        'proposed_rule': 'After any successful publish (OK: response), store the post URL '
                         'in session state and refuse to publish again without explicit new-post intent.',
        'eval_required': 1,
    },
}


def promote_to_learnings(conn):
    """Identify high-frequency signals and create learning entries if not already present."""
    now_ms = int(time.time() * 1000)
    promoted = []

    signal_counts = conn.execute(
        'SELECT signal_type, COUNT(*) n, COUNT(DISTINCT session_id) sessions, '
        'COUNT(DISTINCT user_id) users, GROUP_CONCAT(DISTINCT session_id) session_list '
        'FROM signals GROUP BY signal_type ORDER BY n DESC'
    ).fetchall()

    for row in signal_counts:
        sig_type = row['signal_type']
        if sig_type not in LEARNING_TEMPLATES:
            continue
        if row['n'] < PROMOTE_THRESHOLD:
            continue

        # Check if learning already exists for this signal type
        existing = conn.execute(
            'SELECT learning_id FROM learnings WHERE signal_type = ?', (sig_type,)
        ).fetchone()
        if existing:
            # Update occurrence count
            conn.execute(
                'UPDATE learnings SET occurrence_count = ? WHERE signal_type = ?',
                (row['n'], sig_type)
            )
            continue

        tmpl = LEARNING_TEMPLATES[sig_type]
        session_ids = (row['session_list'] or '').split(',')[:10]
        today = __import__('datetime').date.today().strftime('%Y%m%d')
        # Count existing for today's sequence
        n_today = conn.execute(
            "SELECT COUNT(*) FROM learnings WHERE created_at LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]
        type_prefix = {'error': 'ERR', 'correction': 'CORR', 'pattern': 'PAT', 'feature': 'FEAT'}.get(tmpl['type'], 'UNK')
        learning_id = f"{type_prefix}-{today}-{n_today+1:03d}"

        entry = {
            'learning_id':      learning_id,
            'type':             tmpl['type'],
            'status':           'pending_review',
            'risk_tier':        tmpl['risk_tier'],
            'created_at':       __import__('datetime').datetime.utcnow().isoformat(),
            'promoted_at':      None,
            'user_ids':         json.dumps(list(set(filter(None, [])))),
            'session_ids':      json.dumps(session_ids),
            'bug_id':           None,
            'title':            tmpl['title'],
            'summary':          tmpl['summary'],
            'root_cause':       tmpl['root_cause'],
            'proposed_rule':    tmpl['proposed_rule'],
            'promoted_rule':    None,
            'occurrence_count': row['n'],
            'eval_required':    tmpl.get('eval_required', 0),
            'eval_passed':      None,
            'signal_type':      sig_type,
        }
        conn.execute(
            'INSERT OR REPLACE INTO learnings '
            '(learning_id,type,status,risk_tier,created_at,promoted_at,user_ids,session_ids,'
            'bug_id,title,summary,root_cause,proposed_rule,promoted_rule,occurrence_count,'
            'eval_required,eval_passed,signal_type) VALUES '
            '(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [entry[k] for k in (
                'learning_id','type','status','risk_tier','created_at','promoted_at',
                'user_ids','session_ids','bug_id','title','summary','root_cause',
                'proposed_rule','promoted_rule','occurrence_count','eval_required',
                'eval_passed','signal_type'
            )]
        )
        promoted.append(f"  + {learning_id}: {tmpl['title']}")

    return promoted


# ─── Report ───────────────────────────────────────────────────────────────────

def print_report(conn):
    USERS_MAP = {
        '264468965': 'Andrii (Owner)',
        '373382939': 'Rudolf',
        '547748231': 'Catherine',
    }
    print("=" * 70)
    print("LEARNING LOOP REPORT")
    print("=" * 70)

    print("\n── Per-User Publish Metrics ─────────────────────────────────────────")
    for row in conn.execute('SELECT * FROM v_publish_success_rate'):
        uid = row['user_id'] or 'unknown'
        name = USERS_MAP.get(uid, uid)
        print(f"  {name:30} success:{row['successes']:3} fail:{row['failures']:3} "
              f"retry:{row['retries']:3} rate:{row['success_rate'] or 0:.1%}")

    print("\n── Signal Frequency ─────────────────────────────────────────────────")
    for row in conn.execute(
        'SELECT signal_type, COUNT(*) n, COUNT(DISTINCT session_id) sessions, '
        'COUNT(DISTINCT user_id) users FROM signals GROUP BY signal_type ORDER BY n DESC'
    ):
        bar = '█' * min(row['n'], 20)
        print(f"  {row['signal_type']:30} {bar} {row['n']:4}x ({row['users']}u/{row['sessions']}s)")

    print("\n── Pending Learnings ────────────────────────────────────────────────")
    for row in conn.execute(
        "SELECT learning_id, title, occurrence_count, risk_tier, status "
        "FROM learnings WHERE status != 'archived' ORDER BY occurrence_count DESC"
    ):
        star = '*' if row['status'] == 'pending_review' else ' '
        print(f"  {star} [{row['risk_tier']:6}] {row['learning_id']:25} x{row['occurrence_count']:3}  {row['title'][:40]}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run ingest.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("Running sequential pattern detection…")
    new_signals = detect_sequential_patterns(conn)
    if new_signals:
        cols = list(new_signals[0].keys())
        placeholders = ','.join(['?'] * len(cols))
        conn.executemany(
            f'INSERT OR IGNORE INTO signals ({",".join(cols)}) VALUES ({placeholders})',
            [[s[c] for c in cols] for s in new_signals]
        )
        conn.commit()
        print(f"  Added {len(new_signals)} new sequential signals")
    else:
        print("  No new sequential signals")

    print("\nChecking promotion thresholds…")
    with conn:
        promoted = promote_to_learnings(conn)
    if promoted:
        print('\n'.join(promoted))
    else:
        print("  No new learnings to promote")

    if '--report' in sys.argv:
        print()
        print_report(conn)

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
