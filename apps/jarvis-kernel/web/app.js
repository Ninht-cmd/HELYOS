// HELYOS — interface conversationnelle. Le cerveau est côté serveur (POST /jarvis) :
// classification d'intention + agents + gouvernance A0–A5. Ici : rendu honnête de
// l'état réel du noyau (agents, audit, événements, portefeuille) — rien d'inventé.
// La 3D est une ambiance : import() dynamique, l'UI fonctionne sans WebGL.

const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api = async (u, o) => {
  const r = await fetch(u, o);
  if (!r.ok) throw new Error(`${u} → ${r.status}`);
  return r.json();
};
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------------- vocabulaire ---------------- */
const INTENT_LABEL = {
  portefeuille: 'portefeuille', relance_factures: 'relance de factures',
  creer_business: 'création de business', recherche: 'recherche',
  action_dangereuse: 'action sensible', conversation: 'conversation',
};
// quelle capacité s'illumine pour chaque intention (mappe intention -> agent réel)
const INTENT_AGENT = {
  relance_factures: 'invoice_reminder', creer_business: 'business_scaffolder',
  recherche: 'research',
};
const VERDICT = {
  allow: v => '✓ autorisé',
  deny: v => `✕ refusé${v.rule ? ' · ' + v.rule : ''}`,
  require_validation: v => `⏸ ta validation est requise${v.rule ? ' · ' + v.rule : ''}`,
};
const CHIPS = [
  'Où en sont mes business ?',
  'Relance mes factures impayées',
  'Analyse le marché des posters IA',
  '🛡 Supprime un fichier obsolète',
  '🛡 Fais un virement de 500 €',
];

/* ---------------- éléments ---------------- */
const thread = $('#thread'), stream = $('#stream'), input = $('#q'), sendBtn = $('#send');
let AGENTS = [], scene3D = null, busy = false;
let spark = () => {};

$('#chips').innerHTML = CHIPS.map(c =>
  `<button type="button" class="chip">${esc(c)}</button>`).join('');
document.querySelectorAll('.chip').forEach(c => c.onclick = () => {
  input.value = c.textContent.replace('🛡 ', ''); send();
});

const hr = new Date().getHours();
$('#greet').firstChild.textContent = (hr < 6 ? 'Bonne nuit ' : hr < 18 ? 'Bonjour ' : 'Bonsoir ');
input.focus();

/* ---------------- état réel du noyau ---------------- */
const rel = ts => {
  const s = Math.max(0, (Date.now() / 1000) - ts);
  if (s < 60) return `${Math.round(s)} s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  return `${Math.round(s / 3600)} h`;
};

function renderAgents() {
  $('#agents').innerHTML = AGENTS.map(a => `
    <div class="ag" data-n="${esc(a.name)}" title="${esc(a.description)}">
      <span class="s"></span><b>${esc(a.name)}</b>
      <span class="st">en veille · ${esc(a.required_level)}</span>
    </div>`).join('') || '<div class="empty">aucun agent</div>';
}
const _actTimers = {};
function agentActed(name) {
  const el = document.querySelector(`.ag[data-n="${name}"]`);
  if (!el) return;
  el.classList.add('on');
  el.querySelector('.st').textContent = 'vient d’agir';
  clearTimeout(_actTimers[name]);           // une 2e action relance le chrono au lieu d'être coupée
  _actTimers[name] = setTimeout(() => {
    el.classList.remove('on');
    const a = AGENTS.find(x => x.name === name);
    el.querySelector('.st').textContent = `en veille · ${a ? a.required_level : ''}`;
  }, 6000);
}

// La pastille d'état reflète la DERNIÈRE tentative de contact avec le noyau,
// pas seulement le boot : un noyau tombé en cours de session se voit.
function setOnline(ok) {
  $('#statedot').classList.toggle('off', !ok);
  $('#state').textContent = ok ? 'noyau local · gouvernance active' : 'noyau hors ligne';
}

async function refreshAudit() {
  try {
    const entries = await api('/governance/audit?limit=5');
    setOnline(true);
    $('#audit').innerHTML = entries.length ? entries.slice().reverse().map(e => `
      <div class="row"><div class="l1">
        <span class="pill ${esc(e.decision)}">${esc(e.decision === 'require_validation' ? 'validation' : e.decision)}</span>
        <b>${esc(e.action_type)}</b>
        <span class="when">${e.rule ? esc(e.rule) + ' · ' : ''}il y a ${rel(e.ts)}</span>
      </div></div>`).join('')
      : '<div class="empty">aucune décision pour l’instant</div>';
  } catch (_) { setOnline(false); }   // panneau best-effort : l'échec ne casse pas la conversation
}
async function refreshFlux() {
  try {
    const ev = await api('/events?limit=6');
    setOnline(true);
    $('#flux').innerHTML = ev.length ? ev.slice().reverse().map(e => `
      <div class="row"><div class="l1">
        <b class="mono">${esc(e.name)}</b>
        <span class="when">il y a ${rel(e.ts)}</span>
      </div></div>`).join('')
      : '<div class="empty">aucun événement pour l’instant</div>';
  } catch (_) { setOnline(false); }
}
async function refreshFolio() {
  try {
    const items = await api('/portfolio');
    if (!items.length) {
      $('#folio').innerHTML = '<div class="empty">aucun business enregistré</div>';
      return;
    }
    $('#folio').innerHTML = items.map(b => {
      const rev = b.metrics && 'revenue_eur' in b.metrics ? `${Number(b.metrics.revenue_eur)} €` : null;
      const badge = rev !== null ? rev : `${Number(b.open_tasks) || 0} tâches`;
      return `<div class="row">
        <div class="l1"><b title="${esc(b.name)}">${esc(b.name)}</b>
          <span class="pill n">${esc(badge)}</span></div>
        <div class="l2">${esc(b.status)}</div>
      </div>`;
    }).join('');
  } catch (_) { setOnline(false); }
}

async function boot() {
  try {
    const h = await api('/health');
    $('#ver').textContent = 'v' + h.version;
    setOnline(true);
    AGENTS = await api('/agents');
    renderAgents();
    if (scene3D) scene3D.setAgents(AGENTS);
  } catch (e) {
    setOnline(false);
  }
  refreshAudit(); refreshFlux(); refreshFolio();
  setInterval(() => {
    if (document.visibilityState === 'visible') { refreshAudit(); refreshFlux(); }
  }, 5000);
  setInterval(() => {
    if (document.visibilityState === 'visible') refreshFolio();
  }, 20000);
}

/* ---------------- conversation ---------------- */
function bubble(who, html) {
  const m = document.createElement('div');
  m.className = 'msg ' + who;
  m.innerHTML = `<div class="av">${who === 'u' ? 'E' : 'H'}</div><div class="bubble">${html}</div>`;
  thread.appendChild(m);
  stream.scrollTop = stream.scrollHeight;
  return m.querySelector('.bubble');
}

async function send() {
  const q = input.value.trim();
  if (!q || busy) return;
  busy = true; sendBtn.disabled = true;
  input.value = '';
  document.body.classList.replace('home', 'chat');
  bubble('u', esc(q));
  const b = bubble('j', '<span class="think"><i></i><i></i><i></i></span>');
  spark();
  try {
    const r = await api('/jarvis', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: q, granted_level: $('#lvl').value }),
    });
    const tags = [`<span class="tag intent">${esc(INTENT_LABEL[r.intent] || r.intent)}</span>`];
    if (r.governed && r.decision && VERDICT[r.decision])
      tags.push(`<span class="tag ${esc(r.decision)}">${esc(VERDICT[r.decision](r))}</span>`);
    b.innerHTML = `${esc(r.text)}<div class="meta">${tags.join('')}</div>`;
    const agent = INTENT_AGENT[r.intent];
    // l'agent ne « vient d'agir » que si la gouvernance a laissé passer
    if (agent && (!r.governed || r.decision === 'allow')) { agentActed(agent); spark(agent); }
    refreshAudit(); refreshFlux();          // les panneaux réagissent tout de suite
    if (r.intent === 'creer_business') refreshFolio();
  } catch (e) {
    // une réponse HTTP en erreur ≠ un noyau éteint : on le dit honnêtement
    b.innerHTML = /→ \d{3}$/.test(e.message || '')
      ? `Le noyau a répondu une erreur (${esc(e.message)}). Réessaie ou reformule.`
      : 'Le noyau ne répond pas — vérifie que le kernel tourne '
        + '(<span class="mono">python -m jarvis_kernel</span>).';
    setOnline(!/Failed to fetch|NetworkError|réseau/i.test(e.message || '') && !(e instanceof TypeError));
  } finally {
    busy = false; sendBtn.disabled = false;
    stream.scrollTop = stream.scrollHeight;
    input.focus();
  }
}
$('#form').addEventListener('submit', e => { e.preventDefault(); send(); });

/* ---------------- scène 3D (ambiance, jamais bloquante) ---------------- */
// Le cœur vit dans le TIERS HAUT de l'écran (y=+5.2) : il ne croise jamais le texte.
function makeRadialTex(THREE, inner) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(inner, 'rgba(255,255,255,.5)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
function init3D(THREE) {
  const CY = 8.6;                                     // altitude du cœur (tiers haut, hors du texte)
  const COLORS = [0x6ff7d6, 0x49b6ff, 0xb69bff, 0xffce6a];
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setSize(innerWidth, innerHeight);
  $('#scene').appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x04060a, 0.018);
  const camera = new THREE.PerspectiveCamera(52, innerWidth / innerHeight, 0.1, 300);
  camera.position.set(0, 1.5, 19);

  const glow = makeRadialTex(THREE, .25), dotTex = makeRadialTex(THREE, .5);
  const sprite = (color, scale, tex) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex || glow, color, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    s.scale.set(scale, scale, 1); return s;
  };

  const core = new THREE.Group();
  const ico = new THREE.Mesh(new THREE.IcosahedronGeometry(1.6, 1),
    new THREE.MeshBasicMaterial({ color: 0x6ff7d6, wireframe: true, transparent: true, opacity: .35 }));
  const shell = new THREE.Mesh(new THREE.IcosahedronGeometry(1.1, 2),
    new THREE.MeshBasicMaterial({ color: 0x123a33, transparent: true, opacity: .5 }));
  core.add(sprite(0x6ff7d6, 9), sprite(0xeafff9, 3.2), shell, ico);
  core.position.y = CY;
  scene.add(core);
  let coreAct = 0, t = 0;

  const N = 1500, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const r = 10 + Math.random() * 30, th = Math.random() * 6.283, ph = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th) * .6;
    pos[i * 3 + 2] = r * Math.cos(ph);
  }
  const pg = new THREE.BufferGeometry();
  pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const stars = new THREE.Points(pg, new THREE.PointsMaterial({
    size: .15, map: dotTex, color: 0x9fc7ff, transparent: true, opacity: .5,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  scene.add(stars);

  let nodes = [];
  function setAgents(list) {
    nodes.forEach(n => { scene.remove(n.g); scene.remove(n.line); });
    nodes = list.map((a, i) => {
      const col = COLORS[i % 4], g = new THREE.Group();
      g.add(sprite(col, 1.4), sprite(0xffffff, .5, dotTex));
      scene.add(g);
      const lp = new Float32Array(6);
      lp[0] = 0; lp[1] = CY; lp[2] = 0;               // les liens partent du cœur
      lp[3] = 0; lp[4] = CY; lp[5] = 0;               // et y restent jusqu'au 1er frame
      const lg = new THREE.BufferGeometry();
      lg.setAttribute('position', new THREE.BufferAttribute(lp, 3));
      const line = new THREE.Line(lg, new THREE.LineBasicMaterial({
        color: col, transparent: true, opacity: .18,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      scene.add(line);
      return { name: a.name, g, line, lp, a: (i / list.length) * 6.283,
        r: 3.2 + Math.random() * 0.9, yb: (Math.random() - .5) * 1.3,
        sp: .12 + Math.random() * .12, ph: Math.random() * 6.283, act: 0 };
    });
    if (REDUCED) frame();                              // une image propre, sans boucle
  }

  const mouse = { x: 0, y: 0 }, target = { x: 0, y: 0 };
  if (!REDUCED)
    addEventListener('pointermove', e => {
      target.x = (e.clientX / innerWidth - .5);
      target.y = (e.clientY / innerHeight - .5);
    });
  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    if (REDUCED) frame();
  });

  function frame() {
    t += 0.01; coreAct *= 0.96;
    core.rotation.y += 0.0016;
    const br = 1 + Math.sin(t * 1.2) * 0.03 + coreAct * 0.3;
    core.scale.setScalar(br);
    ico.rotation.y -= 0.004; ico.rotation.z += 0.002;
    stars.rotation.y += 0.0004;
    for (const n of nodes) {
      n.act *= 0.95;
      const ang = n.a + t * n.sp;
      const x = Math.cos(ang) * n.r, z = Math.sin(ang) * n.r;
      const y = CY + n.yb + Math.sin(t * 1.4 + n.ph) * 0.4;
      n.g.position.set(x, y, z);
      const hs = 1.4 + n.act * 2;
      n.g.children[0].scale.set(hs, hs, 1);
      n.lp[3] = x; n.lp[4] = y; n.lp[5] = z;
      n.line.geometry.attributes.position.needsUpdate = true;
      n.line.material.opacity = 0.1 + (Math.sin(t * 2 + n.ph) * .5 + .5) * 0.14 + n.act * 0.5;
    }
    mouse.x += (target.x - mouse.x) * 0.05; mouse.y += (target.y - mouse.y) * 0.05;
    // parallaxe horizontal uniquement : un décalage vertical ferait redescendre
    // le cœur dans la zone de texte.
    camera.position.x = mouse.x * 4;
    camera.lookAt(0, 2.4, 0);
    renderer.render(scene, camera);
  }
  function loop() { frame(); requestAnimationFrame(loop); }
  if (REDUCED) frame(); else loop();

  return {
    setAgents,
    spark(name) {
      coreAct = 1;
      const n = name && nodes.find(x => x.name === name);
      if (n) n.act = 1;
      if (REDUCED) frame();
    },
  };
}

/* ---------------- démarrage ---------------- */
boot();
import('three').then(THREE => {
  try {
    scene3D = init3D(THREE);
    spark = n => scene3D.spark(n);
    if (AGENTS.length) scene3D.setAgents(AGENTS);
  } catch (e) { console.warn('WebGL init échec :', e); }
}).catch(e => { console.warn('Three.js indisponible — fond CSS conservé.', e); });
