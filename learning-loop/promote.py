#!/usr/bin/env python3
"""
Company Brain Learning Loop — Rule Promotion
=============================================
Reads learnings from analysis.db (populated by signal-extract.py)
Promotes reviewed learnings to AGENTS.md or skill files.

Risk tiers:
  low    → auto-promote to AGENTS.md appendix (no eval required)
  medium → create proposal file for human review
  high   → require eval_passed = 1 AND human confirmation

Usage:
  python3 learning-loop/promote.py               # run promotion pipeline
  python3 learning-loop/promote.py --dry-run     # show what would change
  python3 learning-loop/promote.py --review      # list all pending learnings
  python3 learning-loop/promote.py --dump-md     # dump manifest.md for dashboard
"""

import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT  = Path(__file__).parent.parent
DB_PATH    = REPO_ROOT / 'learning-loop' / 'analysis.db'
AGENTS_MD  = REPO_ROOT / 'AGENTS.md'
PROPOSALS  = REPO_ROOT / '.learnings' / 'proposals'
MANIFEST   = REPO_ROOT / '.learnings' / 'manifest.json'

DRY_RUN  = '--dry-run' in sys.argv
REVIEW   = '--review'  in sys.argv
DUMP_MD  = '--dump-md' in sys.argv

LEARNING_SECTION_MARKER = '\n## Promoted Learning Rules\n'


# ─── Helpers ─────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_manifest():
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            pass
    return {'version': 1, 'entries': {}}


def save_manifest(data):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def agents_md_has_section(content):
    return LEARNING_SECTION_MARKER.strip() in content


def append_rule_to_agents_md(rule_text, learning_id, title):
    if not AGENTS_MD.exists():
        print(f"  WARN: {AGENTS_MD} not found — skipping promotion")
        return False
    content = AGENTS_MD.read_text(encoding='utf-8')
    if LEARNING_SECTION_MARKER.strip() not in content:
        content += LEARNING_SECTION_MARKER
        content += '\n<!-- Rules promoted by learning-loop/promote.py -->\n\n'

    # Check if this rule is already there
    if learning_id in content:
        return False  # already promoted

    entry = f"\n### {learning_id}: {title}\n\n{rule_text}\n\n---\n"
    content += entry
    if not DRY_RUN:
        AGENTS_MD.write_text(content, encoding='utf-8')
    return True


def write_proposal(learning_row):
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    fname = PROPOSALS / f"{learning_row['learning_id']}.md"
    content = f"""# PROPOSAL: {learning_row['learning_id']}

**Status:** pending_review  
**Risk:** {learning_row['risk_tier']}  
**Type:** {learning_row['type']}  
**Occurrences:** {learning_row['occurrence_count']}  
**Created:** {learning_row['created_at']}

## Title
{learning_row['title']}

## Summary
{learning_row['summary']}

## Root Cause
{learning_row['root_cause']}

## Proposed Rule
{learning_row['proposed_rule']}

## Sessions
{learning_row['session_ids']}

---
*To promote: set status = 'reviewed' in analysis.db and re-run promote.py*
*To archive: set status = 'archived' in analysis.db*
"""
    if not DRY_RUN:
        fname.write_text(content, encoding='utf-8')
    return str(fname)


# ─── Main pipeline ────────────────────────────────────────────────────────────

def run_promotion(conn):
    manifest = load_manifest()
    results = {'promoted': [], 'proposed': [], 'skipped': [], 'errors': []}
    now_ms = int(time.time() * 1000)

    learnings = conn.execute(
        "SELECT * FROM learnings WHERE status NOT IN ('promoted', 'archived') "
        "ORDER BY occurrence_count DESC"
    ).fetchall()

    for row in learnings:
        lid    = row['learning_id']
        tier   = row['risk_tier']
        status = row['status']
        eval_ok = row['eval_passed']

        if REVIEW:
            print(f"\n{'─'*60}")
            print(f"  ID:         {lid}")
            print(f"  Status:     {status}")
            print(f"  Risk:       {tier}")
            print(f"  Type:       {row['type']}")
            print(f"  Signal:     {row['signal_type']}")
            print(f"  Count:      {row['occurrence_count']}")
            print(f"  Title:      {row['title']}")
            print(f"  Rule:       {(row['proposed_rule'] or '')[:100]}…")
            continue

        # ── Low risk: auto-promote to AGENTS.md ─────────────────────────────
        if tier == 'low' and status in ('pending_review', 'reviewed'):
            if not row['eval_required'] or eval_ok:
                rule_text = row['proposed_rule'] or row['summary']
                did_add = append_rule_to_agents_md(rule_text, lid, row['title'])
                if did_add:
                    print(f"  AUTO-PROMOTED [{tier}] {lid}: {row['title'][:50]}")
                    if not DRY_RUN:
                        conn.execute(
                            "UPDATE learnings SET status='promoted', promoted_at=? WHERE learning_id=?",
                            (now_iso(), lid)
                        )
                    results['promoted'].append(lid)
                    manifest['entries'][lid] = {
                        'status': 'promoted',
                        'promoted_at': now_iso(),
                        'title': row['title'],
                        'risk_tier': tier,
                    }
                else:
                    results['skipped'].append(f"{lid} (already in AGENTS.md)")
            else:
                results['skipped'].append(f"{lid} (eval required, not passed)")

        # ── Medium risk: write proposal, require human ───────────────────────
        elif tier == 'medium' and status == 'pending_review':
            fpath = write_proposal(dict(row))
            print(f"  PROPOSAL    [{tier}] {lid}: written to {fpath}")
            if not DRY_RUN:
                conn.execute(
                    "UPDATE learnings SET status='proposal_written' WHERE learning_id=?",
                    (lid,)
                )
            results['proposed'].append(lid)
            manifest['entries'][lid] = {
                'status': 'proposal_written',
                'title': row['title'],
                'risk_tier': tier,
                'proposal_file': str(fpath),
            }

        elif tier == 'medium' and status == 'reviewed':
            # Human approved medium-risk — promote
            if not row['eval_required'] or eval_ok:
                rule_text = row['proposed_rule'] or row['summary']
                did_add = append_rule_to_agents_md(rule_text, lid, row['title'])
                print(f"  PROMOTED    [{tier}] {lid}: {row['title'][:50]}")
                if not DRY_RUN and did_add:
                    conn.execute(
                        "UPDATE learnings SET status='promoted', promoted_at=? WHERE learning_id=?",
                        (now_iso(), lid)
                    )
                results['promoted'].append(lid)
            else:
                print(f"  SKIP (eval not passed) [{tier}] {lid}")
                results['skipped'].append(lid)

        # ── High risk: only if reviewed AND eval passed ───────────────────────
        elif tier == 'high':
            if status == 'reviewed' and eval_ok == 1:
                rule_text = row['proposed_rule'] or row['summary']
                did_add = append_rule_to_agents_md(rule_text, lid, row['title'])
                print(f"  PROMOTED    [{tier}] {lid}: {row['title'][:50]}")
                if not DRY_RUN and did_add:
                    conn.execute(
                        "UPDATE learnings SET status='promoted', promoted_at=? WHERE learning_id=?",
                        (now_iso(), lid)
                    )
                results['promoted'].append(lid)
            else:
                reasons = []
                if status != 'reviewed':
                    reasons.append('not reviewed')
                if row['eval_required'] and not eval_ok:
                    reasons.append('eval not passed')
                results['skipped'].append(f"{lid} ({', '.join(reasons)})")

    if not DRY_RUN and (results['promoted'] or results['proposed']):
        conn.commit()
        save_manifest(manifest)

    return results


def dump_markdown(conn):
    """Dump a human-readable markdown of all learnings for the dashboard."""
    out = ['# Learning Loop — Manifest\n', f'Generated: {now_iso()}\n']
    learnings = conn.execute(
        "SELECT * FROM learnings ORDER BY "
        "CASE status WHEN 'pending_review' THEN 0 WHEN 'proposal_written' THEN 1 "
        "WHEN 'reviewed' THEN 2 WHEN 'promoted' THEN 3 ELSE 4 END, occurrence_count DESC"
    ).fetchall()

    for row in learnings:
        status_icon = {'promoted':'✅','pending_review':'⏳','archived':'🗃️',
                       'proposal_written':'📋','reviewed':'👍'}.get(row['status'],'❓')
        tier_icon = {'low':'🟢','medium':'🟡','high':'🔴'}.get(row['risk_tier'],'⚪')
        out.append(f"\n## {status_icon} {row['learning_id']} — {row['title']}\n")
        out.append(f"- **Risk:** {tier_icon} {row['risk_tier']}  ")
        out.append(f"- **Type:** {row['type']}  ")
        out.append(f"- **Signal:** `{row['signal_type']}`  ")
        out.append(f"- **Occurrences:** {row['occurrence_count']}  ")
        out.append(f"- **Status:** {row['status']}\n\n")
        if row['summary']:
            out.append(f"**Summary:** {row['summary']}\n\n")
        if row['root_cause']:
            out.append(f"**Root cause:** {row['root_cause']}\n\n")
        if row['proposed_rule']:
            out.append(f"**Proposed rule:**\n> {row['proposed_rule']}\n\n")

    md = '\n'.join(out)
    dest = REPO_ROOT / '.learnings' / 'manifest.md'
    dest.write_text(md, encoding='utf-8')
    print(f"Written: {dest}")
    return md


def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run ingest.py then signal-extract.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if DUMP_MD:
        dump_markdown(conn)
        conn.close()
        return

    if REVIEW:
        print("=== Pending Learnings ===")
        run_promotion(conn)
        conn.close()
        return

    prefix = "[DRY RUN] " if DRY_RUN else ""
    print(f"{prefix}Running learning promotion pipeline…")
    results = run_promotion(conn)

    print(f"\nPromoted:  {len(results['promoted'])} | Proposed: {len(results['proposed'])} "
          f"| Skipped: {len(results['skipped'])}")
    if results['skipped']:
        for s in results['skipped']:
            print(f"  skip: {s}")

    conn.close()


if __name__ == '__main__':
    main()
