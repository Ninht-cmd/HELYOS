"""Tableau de bord HTML du Kernel — page d'accueil humaine (servie à la racine).

Page autonome (HTML+CSS+JS inline, zéro dépendance front). Le JS interroge l'API
même-origine (/health, /agents, /governance/*, /intent). C'est la vitrine *de base*
du cœur ouvert ; le dashboard entreprise avancé reste un module Pro (frontière open/Pro).
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HELYOS — Kernel gouverné</title>
<style>
  :root { --bg:#0b0f0c; --panel:#11161300; --card:#121a15; --line:#1f2a22;
          --txt:#e6f0e8; --muted:#7e8f84; --accent:#7CFC5A; --accent2:#3fb950;
          --deny:#ff6b6b; --warn:#f0b429; --ok:#7CFC5A; }
  * { box-sizing:border-box; }
  body { margin:0; background:radial-gradient(1200px 600px at 70% -10%, #15211a, var(--bg));
         color:var(--txt); font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif; }
  .wrap { max-width:980px; margin:0 auto; padding:28px 20px 60px; }
  header { display:flex; align-items:center; gap:14px; margin-bottom:4px; }
  .logo { font-weight:800; letter-spacing:.5px; font-size:26px; }
  .logo b { color:var(--accent); }
  .pill { font-size:12px; padding:3px 10px; border-radius:999px; border:1px solid var(--line);
          color:var(--muted); }
  .pill.live { color:#04210b; background:var(--accent); border-color:var(--accent); font-weight:700; }
  .sub { color:var(--muted); margin:0 0 22px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:22px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
  .card .k { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.5px; }
  .card .v { font-size:22px; font-weight:700; margin-top:4px; }
  h2 { font-size:14px; text-transform:uppercase; letter-spacing:1px; color:var(--muted);
       border-bottom:1px solid var(--line); padding-bottom:8px; margin:26px 0 14px; }
  .ladder { display:grid; gap:6px; }
  .lvl { display:flex; gap:12px; align-items:center; background:var(--card); border:1px solid var(--line);
         border-radius:8px; padding:8px 12px; }
  .lvl b { color:var(--accent); width:32px; }
  .lvl .lbl { color:var(--muted); }
  .agents { display:flex; flex-wrap:wrap; gap:8px; }
  .tag { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:6px 10px; font-size:13px; }
  .tag span { color:var(--accent2); font-size:11px; }
  form { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .row { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; }
  label { display:block; font-size:12px; color:var(--muted); margin-bottom:4px; }
  select, button { background:#0c130f; color:var(--txt); border:1px solid var(--line);
          border-radius:8px; padding:8px 10px; font:inherit; }
  .checks { display:flex; gap:14px; margin:12px 0; flex-wrap:wrap; }
  .checks label { display:flex; gap:6px; align-items:center; color:var(--txt); }
  button.go { background:var(--accent); color:#04210b; font-weight:700; cursor:pointer; border:none; padding:9px 16px; }
  button.go:hover { background:#9bff80; }
  #verdict { margin-top:14px; padding:14px; border-radius:10px; border:1px solid var(--line);
             background:#0c130f; display:none; }
  #verdict.allow { border-color:var(--ok); }
  #verdict.deny { border-color:var(--deny); }
  #verdict.require_validation { border-color:var(--warn); }
  .dec { font-weight:800; font-size:16px; }
  .dec.allow { color:var(--ok); } .dec.deny { color:var(--deny); } .dec.require_validation { color:var(--warn); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:left; padding:7px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-weight:600; }
  .badge { font-size:11px; padding:2px 7px; border-radius:6px; }
  .badge.allow { background:#0e2a15; color:var(--ok); } .badge.deny { background:#2a0e0e; color:var(--deny); }
  .badge.require_validation { background:#2a230e; color:var(--warn); }
  a { color:var(--accent2); } footer { margin-top:34px; color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo"><b>HELYOS</b> Kernel</div>
    <span class="pill live" id="status">● live</span>
    <span class="pill" id="ver">v—</span>
  </header>
  <p class="sub">Système d'exploitation de l'intelligence personnelle — cœur gouverné (autonomie A0–A5).</p>

  <div class="grid">
    <div class="card"><div class="k">Version</div><div class="v" id="c-ver">—</div></div>
    <div class="card"><div class="k">Agents</div><div class="v" id="c-agents">—</div></div>
    <div class="card"><div class="k">Décisions auditées</div><div class="v" id="c-audit">—</div></div>
    <div class="card"><div class="k">Gouvernance</div><div class="v">A0–A5</div></div>
  </div>

  <h2>Agents enregistrés</h2>
  <div class="agents" id="agents"></div>

  <h2>Tester une intention (gouvernance en direct)</h2>
  <form id="intentForm">
    <div class="row">
      <div><label>Type d'action</label>
        <select id="action_type">
          <option value="read">read (A0)</option>
          <option value="analyze">analyze (A1)</option>
          <option value="write_local">write_local (A2)</option>
          <option value="rename_workdir">rename_workdir (A3)</option>
          <option value="delete" selected>delete (A2 + sauvegarde)</option>
          <option value="external_sensitive">external_sensitive (GR-2)</option>
          <option value="financial">financial (GR-7)</option>
          <option value="self_permission">self_permission (GR-3)</option>
        </select></div>
      <div><label>Niveau accordé</label>
        <select id="granted_level">
          <option>A0</option><option>A1</option><option>A2</option>
          <option>A3</option><option>A4</option><option selected>A5</option>
        </select></div>
      <button class="go" type="submit">Soumettre →</button>
    </div>
    <div class="checks">
      <label><input type="checkbox" id="has_backup"> sauvegarde existe</label>
      <label><input type="checkbox" id="sensitive"> sensible</label>
      <label><input type="checkbox" id="validated"> validé par le Conservateur</label>
    </div>
    <div id="verdict">
      <div class="dec" id="v-dec"></div>
      <div id="v-reason" style="margin-top:6px;color:var(--muted)"></div>
      <div id="v-meta" style="margin-top:6px;font-size:12px;color:var(--muted)"></div>
    </div>
  </form>

  <h2>Journal d'audit (récent)</h2>
  <table><thead><tr><th>Décision</th><th>Action</th><th>Acteur</th><th>Règle</th><th>Requis/Accordé</th></tr></thead>
  <tbody id="audit"></tbody></table>

  <footer>
    API : <a href="/docs">/docs</a> · <a href="/info">/info</a> ·
    <a href="https://github.com/Ninht-cmd/HELYOS" target="_blank">GitHub</a><br>
    « Le Codex est la source de vérité. »
  </footer>
</div>

<script>
const $ = s => document.querySelector(s);
async function j(u, o) { const r = await fetch(u, o); return r.json(); }

async function refresh() {
  try {
    const h = await j('/health');
    $('#ver').textContent = 'v' + h.version;
    $('#c-ver').textContent = h.version;
    const agents = await j('/agents');
    $('#c-agents').textContent = agents.length;
    $('#agents').innerHTML = agents.map(a =>
      `<div class="tag">${a.name} <span>${a.required_level}</span></div>`).join('');
    const levels = await j('/governance/levels'); // (réservé à un usage futur)
    await refreshAudit();
  } catch(e) { $('#status').textContent = '● hors ligne'; $('#status').classList.remove('live'); }
}
async function refreshAudit() {
  const audit = await j('/governance/audit?limit=10');
  $('#c-audit').textContent = audit.length;
  $('#audit').innerHTML = audit.slice().reverse().map(e =>
    `<tr><td><span class="badge ${e.decision}">${e.decision}</span></td>
     <td>${e.action_type}</td><td>${e.actor}</td><td>${e.rule||'—'}</td>
     <td>${e.required_level} / ${e.granted_level}</td></tr>`).join('') ||
    '<tr><td colspan="5" style="color:var(--muted)">Aucune décision encore — teste une intention ci-dessus.</td></tr>';
}

$('#intentForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const body = {
    action_type: $('#action_type').value,
    granted_level: $('#granted_level').value,
    has_backup: $('#has_backup').checked,
    sensitive: $('#sensitive').checked,
    validated: $('#validated').checked,
  };
  const v = await j('/intent', { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(body) });
  const box = $('#verdict'); box.style.display = 'block';
  box.className = v.decision;
  $('#v-dec').className = 'dec ' + v.decision;
  $('#v-dec').textContent = v.decision.toUpperCase();
  $('#v-reason').textContent = v.reason;
  $('#v-meta').textContent = `Requis: ${v.required_level} · Accordé: ${v.granted_level}` + (v.rule ? ` · Règle: ${v.rule}` : '');
  refreshAudit();
});

refresh();
</script>
</body>
</html>"""
