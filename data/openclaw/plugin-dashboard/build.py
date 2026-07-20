#!/usr/bin/env python3
"""
Build script for the Company Brain Analysis Dashboard.
Reads logs/analysis/*.json and generates dist/index.html with embedded data.

Run on pod:    python3 /data/workspace/data/openclaw/plugin-dashboard/build.py
Run locally:   python3 data/openclaw/plugin-dashboard/build.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

PLUGIN_DIR = Path(__file__).parent
DIST_DIR = PLUGIN_DIR / 'dist'

# Analysis dir: three levels up (myagent/logs/analysis/)
ANALYSIS_DIR = (PLUGIN_DIR / '../../../logs/analysis').resolve()


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"  warn: can't read {path.name}: {e}")
        return default or {}


def build():
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    bugs_raw   = load_json(ANALYSIS_DIR / 'bugs.json',           {'bugs': []})
    tasks_raw  = load_json(ANALYSIS_DIR / 'tasks.json',          {'tasks': []})
    users      = load_json(ANALYSIS_DIR / 'users.json',          {})
    sessions   = load_json(ANALYSIS_DIR / 'analysis-state.json', {})
    smap       = load_json(ANALYSIS_DIR / 'session-map.json',    {})

    bugs  = bugs_raw.get('bugs', [])
    tasks = tasks_raw.get('tasks', [])

    data = {
        'bugs':        bugs,
        'tasks':       tasks,
        'users':       users,
        'sessions':    sessions,
        'session_map': smap,
        'built_at':    datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'stats': {
            'total_bugs':        len(bugs),
            'open_bugs':         sum(1 for b in bugs  if b.get('status') == 'open'),
            'resolved_bugs':     sum(1 for b in bugs  if b.get('status') == 'resolved'),
            'total_tasks':       len(tasks),
            'open_tasks':        sum(1 for t in tasks if t.get('status') == 'open'),
            'done_tasks':        sum(1 for t in tasks if t.get('status') == 'done'),
            'total_sessions':    len(smap),
            'analyzed_sessions': sum(1 for s in sessions.values() if s.get('analyzed')),
            'total_users':       len(users),
        },
    }

    data_js  = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    html     = HTML_TEMPLATE.replace('/*__DATA__*/', f'const DATA={data_js};')
    out_path = DIST_DIR / 'index.html'
    out_path.write_text(html, encoding='utf-8')

    s = data['stats']
    print(f"Built {out_path} ({len(html):,} bytes) | {data['built_at']}")
    print(f"  bugs    {s['open_bugs']} open / {s['total_bugs']} total")
    print(f"  tasks   {s['open_tasks']} open / {s['total_tasks']} total")
    print(f"  sessions {s['analyzed_sessions']}/{s['total_sessions']} analyzed")


# ─────────────────────────────────────────────────────────────────────────────
# HTML template — DO NOT EDIT below except for styling / layout changes.
# Data is injected via /*__DATA__*/ placeholder.
# ─────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Company Brain — Dashboard</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d1117;--bg2:#161b22;--bg3:#1c2128;--bd:#30363d;--bd2:#21262d;
  --tx:#e6edf3;--tx2:#8b949e;--tx3:#6e7681;
  --blue:#58a6ff;--green:#3fb950;--yellow:#d29922;--orange:#db6d28;--red:#f85149;--purple:#a371f7;
  --ff:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
}
html,body{background:var(--bg);color:var(--tx);font-family:var(--ff);font-size:14px;line-height:1.5;min-height:100vh}

/* ── Layout ── */
.app{max-width:1440px;margin:0 auto;padding:20px 16px}

/* ── Header ── */
.hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;
     padding-bottom:14px;border-bottom:1px solid var(--bd)}
.hdr-l h1{font-size:18px;font-weight:600;display:flex;align-items:center;gap:8px}
.hdr-l h1 em{color:var(--blue);font-style:normal}
.hdr-meta{font-size:11px;color:var(--tx2);margin-top:3px}
.btn{background:var(--bg2);border:1px solid var(--bd);color:var(--tx);padding:5px 12px;
     border-radius:6px;cursor:pointer;font-size:12px;transition:background .15s}
.btn:hover{background:var(--bg3)}
.live-badge{font-size:10px;padding:2px 7px;border-radius:10px;margin-left:6px;
            background:#0d2d0d;color:var(--green);border:1px solid #1a4a1a;display:none}

/* ── Stats row ── */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:18px}
.stat{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:14px 16px}
.stat-v{font-size:26px;font-weight:700;line-height:1;margin-bottom:2px}
.stat-l{font-size:11px;color:var(--tx2)}

/* ── Grid ── */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.grid3{display:grid;grid-template-columns:380px 1fr;gap:14px}
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}}

/* ── Panel ── */
.panel{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;overflow:hidden}
.ph{display:flex;align-items:center;justify-content:space-between;
    padding:10px 14px;border-bottom:1px solid var(--bd)}
.pt{font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.5px}
.pc{background:var(--bd);color:var(--tx2);border-radius:10px;padding:1px 8px;font-size:11px}

/* ── Badges ── */
.b{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:500;white-space:nowrap}
.b-critical{background:#3d1010;color:var(--red);border:1px solid #5a1515}
.b-high{background:#2d1b00;color:var(--orange);border:1px solid #4a2c00}
.b-medium{background:#2a2200;color:var(--yellow);border:1px solid #403300}
.b-low{background:#0d2d0d;color:var(--green);border:1px solid #1a4a1a}
.b-resolved,.b-done{background:#0d2d1a;color:var(--green);border:1px solid #1a4a2a}
.b-open{background:#0d1b2d;color:var(--blue);border:1px solid #1a2e4a}
.b-in_progress{background:#1e1b2d;color:var(--purple);border:1px solid #2d2a4a}
.b-P1{background:#3d1010;color:var(--red);border:1px solid #5a1515}
.b-P2{background:#2d1b00;color:var(--orange);border:1px solid #4a2c00}
.b-P3{background:#2a2200;color:var(--yellow);border:1px solid #403300}
.b-trivial{background:#0d2d0d;color:var(--green);border:1px solid #1a4a1a}

/* ── Bug list ── */
.bug{display:flex;gap:10px;padding:10px 14px;border-bottom:1px solid var(--bd2);transition:background .1s;cursor:default}
.bug:last-child{border-bottom:none}
.bug:hover{background:var(--bg3)}
.bug-id{font-size:11px;color:var(--tx3);font-family:monospace;min-width:66px;padding-top:1px;flex-shrink:0}
.bug-body{flex:1;min-width:0}
.bug-title{font-size:13px;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis}
.bug-title.resolved{text-decoration:line-through;color:var(--tx2)}
.bug-meta{display:flex;gap:5px;flex-wrap:wrap;align-items:center}
.bug-desc{font-size:11px;color:var(--tx2);margin-top:4px;line-height:1.4;display:none}
.bug:hover .bug-desc{display:block}

/* ── Task list ── */
.task{display:flex;align-items:flex-start;gap:8px;padding:9px 14px;
      border-bottom:1px solid var(--bd2);transition:background .1s}
.task:last-child{border-bottom:none}
.task:hover{background:var(--bg3)}
.task-id{font-size:11px;color:var(--tx3);font-family:monospace;min-width:72px;flex-shrink:0;padding-top:1px}
.task-title{flex:1;font-size:13px}
.task-title.done{text-decoration:line-through;color:var(--tx2)}
.task-effort{font-size:11px;color:var(--tx3);flex-shrink:0}

/* ── Users ── */
.users-wrap{padding:12px}
.ucard{background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:12px;margin-bottom:8px}
.ucard:last-child{margin-bottom:0}
.u-hdr{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:8px}
.u-name{font-size:13px;font-weight:600}
.u-uid{font-size:11px;color:var(--tx3);font-family:monospace;margin-top:1px}
.u-role{font-size:11px;color:var(--tx2)}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}
.d-green{background:var(--green);box-shadow:0 0 6px var(--green)}
.d-yellow{background:var(--yellow);box-shadow:0 0 6px var(--yellow)}
.d-red{background:var(--red);box-shadow:0 0 6px var(--red)}
.d-blue{background:var(--blue)}
.d-gray{background:var(--tx3)}
.u-checks{display:grid;grid-template-columns:1fr 1fr;gap:3px}
.uc{font-size:11px;display:flex;align-items:center;gap:4px}
.uc-ok{color:var(--green)}
.uc-warn{color:var(--yellow)}
.uc-err{color:var(--red)}

/* ── Sessions ── */
.sess-wrap{padding:14px}
.prog-bar-bg{background:var(--bg);border-radius:4px;height:8px;overflow:hidden;margin:8px 0}
.prog-bar{height:100%;background:linear-gradient(90deg,var(--blue),var(--purple));border-radius:4px;transition:width .5s ease}
.prog-row{display:flex;justify-content:space-between;font-size:12px;color:var(--tx2)}
.by-user{font-size:11px;color:var(--tx2);margin-bottom:12px}

/* ── Session table ── */
.stbl{width:100%;border-collapse:collapse;font-size:12px}
.stbl th{text-align:left;padding:5px 8px;color:var(--tx2);font-weight:500;border-bottom:1px solid var(--bd)}
.stbl td{padding:5px 8px;border-bottom:1px solid var(--bd2)}
.stbl tr:last-child td{border-bottom:none}
.stbl tr:hover td{background:var(--bg3)}
.mono{font-family:monospace;font-size:11px}

/* ── Scroll ── */
.scroll{max-height:420px;overflow-y:auto}
.scroll::-webkit-scrollbar{width:4px}
.scroll::-webkit-scrollbar-track{background:transparent}
.scroll::-webkit-scrollbar-thumb{background:var(--bd);border-radius:2px}

/* ── Section title ── */
.section{margin-bottom:8px;font-size:11px;font-weight:600;color:var(--tx3);
         text-transform:uppercase;letter-spacing:.5px;padding:0 14px}
</style>
</head>
<body>
<div class="app">

  <!-- Header -->
  <div class="hdr">
    <div class="hdr-l">
      <h1>🧠 Company <em>Brain</em> — Analysis Dashboard</h1>
      <div class="hdr-meta" id="meta"></div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="live-badge" id="live-badge">● LIVE</span>
      <button class="btn" onclick="tryFetch()">↻ Refresh</button>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats" id="stats"></div>

  <!-- Bugs + Tasks -->
  <div class="grid2">
    <div class="panel">
      <div class="ph"><span class="pt">Bugs</span><span class="pc" id="bug-ct"></span></div>
      <div class="scroll" id="bugs"></div>
    </div>
    <div class="panel">
      <div class="ph"><span class="pt">Improvement Tasks</span><span class="pc" id="task-ct"></span></div>
      <div class="scroll" id="tasks"></div>
    </div>
  </div>

  <!-- Users + Sessions -->
  <div class="grid3">
    <div class="panel">
      <div class="ph"><span class="pt">Users</span><span class="pc" id="user-ct"></span></div>
      <div class="users-wrap" id="users"></div>
    </div>
    <div class="panel">
      <div class="ph"><span class="pt">Session Analysis Progress</span></div>
      <div class="sess-wrap">
        <div class="prog-row" id="prog-row"></div>
        <div class="prog-bar-bg"><div class="prog-bar" id="prog-bar" style="width:0%"></div></div>
        <div class="by-user" id="by-user"></div>
        <table class="stbl">
          <thead><tr>
            <th>File</th><th>User</th><th>Topic</th><th>Date</th><th>Bugs found</th>
          </tr></thead>
          <tbody id="sess-rows"></tbody>
        </table>
      </div>
    </div>
  </div>

</div>
<script>
/*__DATA__*/

const SEV_ORDER={critical:0,high:1,medium:2,low:3};
const UNAMES={'264468965':'Andrii','373382939':'Rudolf','547748231':'Catherine'};

function badge(cls,label){return`<span class="b b-${cls}">${label}</span>`}
function sevBadge(s){return badge(s,s.toUpperCase())}
function stBadge(s){
  if(s==='resolved')return badge('resolved','✓ resolved');
  if(s==='done')return badge('done','✓ done');
  if(s==='open')return badge('open','open');
  if(s==='in_progress')return badge('in_progress','in progress');
  return s;
}
function priBadge(p){return badge(p,p)}
function effort(e){
  const map={trivial:'5min',small:'~1h',medium:'~1d',large:'2d+'};
  return map[e]||e||'';
}

function render(d){
  const {bugs,tasks,users,sessions,session_map,stats,built_at}=d;

  // meta
  document.getElementById('meta').textContent=
    `Built: ${built_at} · v${stats.total_sessions} sessions · ${stats.total_users} users`;

  // stats
  const sd=[
    {v:stats.total_sessions,    l:'Sessions total',   c:'var(--blue)'},
    {v:`${stats.analyzed_sessions}/${stats.total_sessions}`, l:'Analyzed', c:'var(--purple)'},
    {v:stats.open_bugs,         l:'Open bugs',        c:stats.open_bugs>5?'var(--orange)':'var(--yellow)'},
    {v:stats.resolved_bugs,     l:'Resolved bugs',    c:'var(--green)'},
    {v:stats.open_tasks,        l:'Open tasks',       c:'var(--tx)'},
    {v:stats.done_tasks,        l:'Done tasks',       c:'var(--green)'},
  ];
  document.getElementById('stats').innerHTML=sd.map(s=>
    `<div class="stat"><div class="stat-v" style="color:${s.c}">${s.v}</div><div class="stat-l">${s.l}</div></div>`
  ).join('');

  // bugs
  document.getElementById('bug-ct').textContent=`${stats.open_bugs} open / ${stats.total_bugs} total`;
  const sortedBugs=[...bugs].sort((a,b)=>{
    if(a.status==='resolved'&&b.status!=='resolved')return 1;
    if(b.status==='resolved'&&a.status!=='resolved')return -1;
    return(SEV_ORDER[a.severity]||9)-(SEV_ORDER[b.severity]||9);
  });
  document.getElementById('bugs').innerHTML=sortedBugs.map(b=>{
    const res=b.status==='resolved';
    const ulist=(b.affected_users||[]).map(u=>UNAMES[u]||u).join(', ');
    const shortDesc=(b.description||'').substring(0,120)+(b.description?.length>120?'…':'');
    return`<div class="bug">
      <span class="bug-id">${b.id}</span>
      <div class="bug-body">
        <div class="bug-title${res?' resolved':''}">${b.title}</div>
        <div class="bug-meta">
          ${sevBadge(b.severity)}
          ${stBadge(b.status)}
          ${ulist?`<span style="font-size:11px;color:var(--tx3)">👤 ${ulist}</span>`:''}
        </div>
        ${shortDesc?`<div class="bug-desc">${shortDesc}</div>`:''}
      </div>
    </div>`;
  }).join('');

  // tasks
  document.getElementById('task-ct').textContent=`${stats.open_tasks} open / ${stats.total_tasks} total`;
  const sortedTasks=[...tasks].sort((a,b)=>{
    const po={P1:0,P2:1,P3:2,trivial:3};
    if(a.status==='done'&&b.status!=='done')return 1;
    if(b.status==='done'&&a.status!=='done')return -1;
    return(po[a.priority]||9)-(po[b.priority]||9);
  });
  document.getElementById('tasks').innerHTML=sortedTasks.map(t=>`
    <div class="task">
      <span class="task-id">${t.id}</span>
      <span class="task-title${t.status==='done'?' done':''}">${t.title}</span>
      ${priBadge(t.priority)}
      <span class="task-effort">${effort(t.effort)}</span>
    </div>`
  ).join('');

  // users
  document.getElementById('user-ct').textContent=`${stats.total_users} registered`;
  const USER_DEF={
    '264468965':{name:'Andrii (Owner)',role:'owner',
      checks:[
        {ok:true, l:'Approved & active'},
        {ok:true, l:'LinkedIn linked'},
        {ok:true, l:'Brand voice ✓'},
        {ok:true, l:'Strategy ✓'},
      ]},
    '373382939':{name:'Rudolf',role:'approved_user',
      checks:[
        {ok:true,  l:'Approved'},
        {ok:false, l:'LinkedIn not linked'},
        {ok:false, l:'No brand voice'},
        {ok:false, l:'No strategy'},
      ]},
    '547748231':{name:'Catherine Miliutenko',role:'approved_user',
      checks:[
        {ok:true, l:'Approved (fixed ✓)'},
        {ok:true, l:'LinkedIn linked'},
        {ok:true, l:'Brand voice ✓'},
        {ok:true, l:'Strategy created ✓'},
      ]},
  };
  document.getElementById('users').innerHTML=Object.entries(USER_DEF).map(([uid,u])=>{
    const all=u.checks.every(c=>c.ok);
    const any=u.checks.some(c=>!c.ok);
    const dotCls=all?'d-green':any?'d-yellow':'d-red';
    return`<div class="ucard">
      <div class="u-hdr">
        <div>
          <div class="u-name">${u.name}</div>
          <div class="u-uid">${uid}</div>
          <div class="u-role">${u.role}</div>
        </div>
        <span class="dot ${dotCls}"></span>
      </div>
      <div class="u-checks">
        ${u.checks.map(c=>`
          <div class="uc ${c.ok?'uc-ok':'uc-warn'}">${c.ok?'✓':'⚠'} ${c.l}</div>
        `).join('')}
      </div>
    </div>`;
  }).join('');

  // sessions progress
  const total=stats.total_sessions||37;
  const done=stats.analyzed_sessions||0;
  const pct=total?Math.round(done/total*100):0;
  document.getElementById('prog-row').innerHTML=
    `<span>${done} analyzed</span><span>${pct}% (${total-done} remaining)</span>`;
  document.getElementById('prog-bar').style.width=pct+'%';

  // by-user breakdown
  const byUser={};
  Object.values(sessions).forEach(s=>{
    if(!s.analyzed)return;
    const u=UNAMES[s.user_id]||'Unknown';
    byUser[u]=(byUser[u]||0)+1;
  });
  document.getElementById('by-user').textContent=
    'By user: '+(Object.entries(byUser).map(([u,c])=>`${u} (${c})`).join(' · ')||'none yet');

  // session table — analyzed sessions sorted by date desc
  const analyzed=Object.values(sessions)
    .filter(s=>s.analyzed)
    .sort((a,b)=>(b.date||'').localeCompare(a.date||''))
    .slice(0,12);

  document.getElementById('sess-rows').innerHTML=analyzed.map(s=>{
    const bugs=(s.bugs_referenced||[]).join(', ')||`${(s.findings||[]).length} findings`;
    const short=(s.file||'').replace(/\.jsonl.*/,'').substring(0,14)+'…';
    const topicLabel=s.topic?`topic-${s.topic}`:(s.session_key||'').split(':').slice(-1)[0]||'—';
    return`<tr>
      <td class="mono">${short}</td>
      <td>${UNAMES[s.user_id]||'?'}</td>
      <td>${topicLabel}</td>
      <td style="color:var(--tx2)">${s.date||'?'}</td>
      <td style="color:var(--tx2)">${bugs}</td>
    </tr>`;
  }).join('');
}

async function tryFetch(){
  try{
    const [b,t,u,s]=await Promise.all([
      fetch('./data/bugs.json'),
      fetch('./data/tasks.json'),
      fetch('./data/users.json'),
      fetch('./data/analysis-state.json'),
    ]);
    if(!b.ok)throw new Error('fetch failed');
    const bd=await b.json(), td=await t.json(), ud=await u.json(), sd=await s.json();
    const bugs=bd.bugs||[], tasks=td.tasks||[];
    const nd={...DATA,bugs,tasks,users:ud,sessions:sd,
      built_at:DATA.built_at+' (live)',
      stats:{...DATA.stats,
        total_bugs:bugs.length,
        open_bugs:bugs.filter(x=>x.status==='open').length,
        resolved_bugs:bugs.filter(x=>x.status==='resolved').length,
        total_tasks:tasks.length,
        open_tasks:tasks.filter(x=>x.status==='open').length,
        done_tasks:tasks.filter(x=>x.status==='done').length,
        total_sessions:Object.keys(sd).length||DATA.stats.total_sessions,
        analyzed_sessions:Object.values(sd).filter(x=>x.analyzed).length,
      }};
    document.getElementById('live-badge').style.display='inline';
    render(nd);
  }catch(e){
    render(DATA); // fallback to embedded
  }
}

render(DATA);
</script>
</body>
</html>'''


if __name__ == '__main__':
    build()
