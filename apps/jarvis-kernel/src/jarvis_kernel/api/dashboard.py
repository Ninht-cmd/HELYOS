"""Interface HELYOS — l'incarnation (Jarvis), pas un dashboard d'admin.

Page autonome (HTML+CSS+Canvas+JS, zéro dépendance front, local-first : aucun CDN).
Conception : conversation au centre, fond vivant (graphe cognitif animé), agents
visibles au travail, et la gouvernance A0–A5 qui se *ressent* dans le dialogue.

Le JS interroge l'API même-origine (réel : /health, /agents, /governance/*, /intent).
Les signaux d'environnement (PC/GPU/Docker…) sont un APERÇU — connecteurs à venir.
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>HELYOS</title>
<style>
  :root{
    --bg0:#05070b; --bg1:#0a1018; --ink:#eaf1fb; --muted:#8a98ad; --faint:#566273;
    --mint:#6ff7d6; --cyan:#49b6ff; --violet:#b69bff; --amber:#ffce6a; --coral:#ff7a8a;
    --glass:rgba(255,255,255,.045); --glass2:rgba(255,255,255,.07); --line:rgba(255,255,255,.09);
    --spring:cubic-bezier(.22,1,.36,1);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{background:var(--bg0);color:var(--ink);overflow:hidden;
    font-family:-apple-system,"SF Pro Display","Segoe UI",Inter,system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;letter-spacing:.2px}
  canvas#bg{position:fixed;inset:0;width:100%;height:100%;z-index:0;display:block}
  .vignette{position:fixed;inset:0;z-index:1;pointer-events:none;
    background:radial-gradient(120% 90% at 50% 8%,transparent 40%,rgba(0,0,0,.55) 100%)}
  .scene{position:fixed;inset:0;z-index:2;display:flex;flex-direction:column}

  /* ---- rail des univers ---- */
  .rail{position:fixed;left:0;top:0;bottom:0;width:64px;z-index:5;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:6px;padding:14px 0}
  .rail .u{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:18px;
    color:var(--muted);background:transparent;border:1px solid transparent;cursor:pointer;
    transition:.35s var(--spring)}
  .rail .u:hover{color:var(--ink);background:var(--glass);border-color:var(--line);transform:translateX(3px)}
  .rail .u.on{color:#04221b;background:linear-gradient(180deg,var(--mint),#39d3b3);box-shadow:0 6px 22px rgba(111,247,214,.32)}
  .rail .tip{position:absolute;left:60px;white-space:nowrap;background:#0c131d;border:1px solid var(--line);
    padding:5px 10px;border-radius:9px;font-size:12px;color:var(--ink);opacity:0;transform:translateX(-6px);
    transition:.25s var(--spring);pointer-events:none}
  .rail .u:hover .tip{opacity:1;transform:translateX(0)}

  /* ---- topbar minimale ---- */
  .top{position:fixed;top:0;left:64px;right:0;z-index:5;display:flex;align-items:center;gap:14px;
    padding:18px 26px;font-size:13px;color:var(--muted)}
  .brand{font-weight:700;letter-spacing:3px;color:var(--ink)}
  .brand b{color:var(--mint)}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--mint);box-shadow:0 0 12px var(--mint);
    animation:bp 2.4s infinite}
  @keyframes bp{0%,100%{opacity:1}50%{opacity:.35}}
  .top .sp{flex:1}
  .top a{color:var(--faint);text-decoration:none;transition:.3s}.top a:hover{color:var(--mint)}

  /* ---- coeur : hero + conversation ---- */
  .center{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:0 24px 0 88px;position:relative}
  .hero{text-align:center;max-width:720px;transition:.7s var(--spring)}
  .hero.lift{transform:translateY(-22vh) scale(.86);opacity:.0;pointer-events:none}
  .greet{font-size:clamp(34px,6vw,62px);font-weight:300;line-height:1.05;
    background:linear-gradient(180deg,#fff,#aebbcd);-webkit-background-clip:text;background-clip:text;
    -webkit-text-fill-color:transparent;animation:rise .9s var(--spring) both}
  .greet .nm{font-weight:600;background:linear-gradient(120deg,var(--mint),var(--cyan));
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  .ask{margin-top:14px;color:var(--muted);font-size:clamp(15px,2vw,19px);font-weight:300;
    animation:rise 1s .1s var(--spring) both}
  @keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}

  .composer{margin-top:34px;width:min(680px,86vw);position:relative;animation:rise 1.1s .2s var(--spring) both}
  .composer .ring{position:absolute;inset:-1px;border-radius:18px;padding:1px;
    background:conic-gradient(from 0deg,var(--mint),var(--cyan),var(--violet),var(--mint));
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;opacity:.5;animation:spin 8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .composer form{position:relative;display:flex;align-items:center;gap:10px;background:rgba(10,16,24,.72);
    backdrop-filter:blur(18px);border:1px solid var(--line);border-radius:18px;padding:8px 8px 8px 18px;
    box-shadow:0 24px 60px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.05)}
  .composer .pulse{width:11px;height:11px;border-radius:50%;flex:none;
    background:radial-gradient(circle at 35% 35%,#fff,var(--mint));box-shadow:0 0 16px var(--mint);
    animation:bp 2s infinite}
  .composer input{flex:1;background:transparent;border:0;outline:0;color:var(--ink);font-size:17px;
    padding:12px 0;font-family:inherit}
  .composer input::placeholder{color:var(--faint)}
  .composer .send{flex:none;width:42px;height:42px;border-radius:13px;border:0;cursor:pointer;color:#04221b;
    background:linear-gradient(160deg,var(--mint),#34c9a8);font-size:18px;transition:.3s var(--spring)}
  .composer .send:hover{filter:brightness(1.12);transform:scale(1.06)}
  .chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:16px;animation:rise 1.2s .3s var(--spring) both}
  .chip{font-size:12.5px;color:var(--muted);background:var(--glass);border:1px solid var(--line);
    padding:7px 12px;border-radius:11px;cursor:pointer;transition:.3s var(--spring)}
  .chip:hover{color:var(--ink);border-color:var(--mint);transform:translateY(-2px)}

  /* ---- flux de conversation ---- */
  .stream{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;
    padding:90px 24px 220px 112px;overflow:auto}
  .stream.show{display:flex}
  .thread{width:min(720px,90vw);display:flex;flex-direction:column;gap:18px}
  .msg{display:flex;gap:12px;align-items:flex-start;animation:rise .5s var(--spring) both}
  .msg .av{width:30px;height:30px;border-radius:9px;flex:none;display:grid;place-items:center;font-size:13px;font-weight:700}
  .msg.u{flex-direction:row-reverse}
  .msg.u .bubble{background:rgba(73,182,255,.10);border-color:rgba(73,182,255,.28)}
  .msg.u .av{background:rgba(73,182,255,.16);color:var(--cyan)}
  .msg.j .av{background:linear-gradient(160deg,var(--mint),#2bbfa0);color:#04221b}
  .bubble{background:var(--glass);border:1px solid var(--line);border-radius:14px;padding:13px 16px;
    font-size:15px;line-height:1.55;max-width:78%}
  .bubble .v{display:inline-flex;align-items:center;gap:8px;margin-top:9px;font-size:12.5px;
    padding:5px 10px;border-radius:9px;font-weight:600}
  .v.allow{background:rgba(111,247,214,.12);color:var(--mint)}
  .v.deny{background:rgba(255,122,138,.12);color:var(--coral)}
  .v.require_validation{background:rgba(255,206,106,.12);color:var(--amber)}
  .think{display:inline-flex;gap:5px;align-items:center;color:var(--muted);font-size:14px}
  .think i{width:6px;height:6px;border-radius:50%;background:var(--mint);animation:th 1s infinite}
  .think i:nth-child(2){animation-delay:.15s}.think i:nth-child(3){animation-delay:.3s}
  @keyframes th{0%,100%{opacity:.25;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}

  /* ---- panneaux vivants ---- */
  .panel{position:fixed;z-index:4;background:rgba(9,14,21,.55);backdrop-filter:blur(16px);
    border:1px solid var(--line);border-radius:16px;padding:14px 15px;
    box-shadow:0 18px 50px rgba(0,0,0,.4);transition:.6s var(--spring)}
  .panel h4{font-size:11px;text-transform:uppercase;letter-spacing:1.4px;color:var(--faint);
    margin-bottom:11px;display:flex;align-items:center;gap:7px}
  .panel h4 .d{width:6px;height:6px;border-radius:50%}
  .agents{left:88px;top:96px;width:248px}
  .agents .d{background:var(--mint)}
  .ag{margin-bottom:12px}
  .ag .r{display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px}
  .ag .r b{font-weight:600}.ag .r span{color:var(--faint);font-size:11.5px}
  .bar{height:5px;border-radius:4px;background:rgba(255,255,255,.07);overflow:hidden}
  .bar i{display:block;height:100%;width:0;border-radius:4px;
    background:linear-gradient(90deg,var(--mint),var(--cyan));transition:width .9s var(--spring)}

  .thoughts{right:26px;top:96px;width:266px}
  .thoughts .d{background:var(--violet)}
  .thoughts .t{font-size:13px;color:var(--muted);line-height:1.5;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05);
    animation:rise .5s var(--spring) both}
  .thoughts .t b{color:var(--violet);font-weight:500}

  .world{right:26px;bottom:26px;width:266px}
  .world .d{background:var(--cyan)}
  .world .n{display:flex;align-items:center;gap:9px;font-size:13px;padding:6px 0;color:var(--muted)}
  .world .n .s{width:7px;height:7px;border-radius:50%;flex:none}
  .world .n .s.off{background:var(--faint)} .world .n .s.on{background:var(--mint);box-shadow:0 0 8px var(--mint)}
  .world .n em{margin-left:auto;font-style:normal;font-size:11px;color:var(--faint)}

  .goals{left:88px;bottom:26px;width:248px}
  .goals .d{background:var(--amber)}
  .goals .g{font-size:13px;margin-bottom:9px}
  .goals .g .r{display:flex;justify-content:space-between;margin-bottom:5px;color:var(--ink)}
  .goals .g .r span{color:var(--amber);font-weight:600}
  .goals .bar i{background:linear-gradient(90deg,var(--amber),#ff9f6b)}

  .panel.hide{opacity:0;transform:translateY(10px);pointer-events:none}
  .note{position:fixed;bottom:8px;left:0;right:0;text-align:center;z-index:3;font-size:11px;color:var(--faint)}
  @media(max-width:1080px){.thoughts,.world{display:none}}
  @media(max-width:780px){.agents,.goals{display:none}.center{padding-left:24px}.rail{display:none}.top{left:0}.stream{padding-left:24px}}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<div class="vignette"></div>

<nav class="rail" id="rail"></nav>

<div class="top">
  <span class="brand"><b>H</b>ELYOS</span>
  <span class="dot"></span><span id="state">intelligence active</span>
  <span class="sp"></span>
  <span id="ver">v—</span><a href="/docs">API</a><a href="/info">info</a>
</div>

<div class="scene">
  <div class="center">
    <div class="hero" id="hero">
      <div class="greet" id="greet">Bonjour <span class="nm">Emeric</span>.</div>
      <div class="ask">Que souhaites-tu accomplir aujourd'hui&nbsp;?</div>
      <div class="composer">
        <div class="ring"></div>
        <form id="form">
          <div class="pulse"></div>
          <input id="q" autocomplete="off" placeholder="Parle à HELYOS…  « analyse un contrat », « supprime un fichier », « prépare une RFC »">
          <button class="send" type="submit">↑</button>
        </form>
      </div>
      <div class="chips" id="chips"></div>
    </div>

    <div class="stream" id="stream"><div class="thread" id="thread"></div></div>
  </div>
</div>

<!-- panneaux vivants -->
<aside class="panel agents"><h4><span class="d"></span>Agents</h4><div id="agents"></div></aside>
<aside class="panel thoughts"><h4><span class="d"></span>Ce que Jarvis pense</h4><div id="thoughts"></div></aside>
<aside class="panel world"><h4><span class="d"></span>Mon monde <em style="margin-left:auto;font-size:10px;color:var(--faint)">aperçu</em></h4><div id="world"></div></aside>
<aside class="panel goals"><h4><span class="d"></span>Objectifs</h4><div id="goals"></div></aside>

<div class="note">HELYOS — incarnation gouvernée · les actions passent par la gouvernance A0–A5 · environnement « Mon monde » = aperçu (connecteurs à venir)</div>

<script>
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const api=async(u,o)=>{const r=await fetch(u,o);return r.json();};

/* ====================== FOND COGNITIF (canvas) ====================== */
const cv=$('#bg'), ctx=cv.getContext('2d');
let W,H,DPR,nodes=[],parts=[],core,mouse={x:.5,y:.5},tmouse={x:.5,y:.5},t=0;
const PAL={mint:'#6ff7d6',cyan:'#49b6ff',violet:'#b69bff',amber:'#ffce6a'};
function resize(){DPR=Math.min(devicePixelRatio||1,2);W=cv.width=innerWidth*DPR;H=cv.height=innerHeight*DPR;
  cv.style.width=innerWidth+'px';cv.style.height=innerHeight+'px';}
addEventListener('resize',resize);resize();
addEventListener('pointermove',e=>{tmouse.x=e.clientX/innerWidth;tmouse.y=e.clientY/innerHeight;});

function seedScene(labels){
  const cx=W*.5, cy=H*.52;
  core={x:cx,y:cy,r:34*DPR,act:0,pa:0};
  nodes=labels.map((l,i)=>{const a=(i/labels.length)*Math.PI*2 - Math.PI/2;
    const rad=(150+Math.random()*120)*DPR;
    return{label:l,a,rad,x:cx+Math.cos(a)*rad,y:cy+Math.sin(a)*rad,
      r:(6+Math.random()*5)*DPR,act:0,sp:.15+Math.random()*.25,ph:Math.random()*6.28,col:Object.values(PAL)[i%4]};});
  parts=Array.from({length:130},()=>({x:Math.random()*W,y:Math.random()*H,
    vx:(Math.random()-.5)*.12*DPR,vy:(Math.random()-.5)*.12*DPR,r:Math.random()*1.5*DPR+.3,al:Math.random()*.5+.1}));
}
function hex(c,a){a=a<0?0:a>1?1:a;return c+Math.round(a*255).toString(16).padStart(2,'0');}
function glow(x,y,r,c,a){const g=ctx.createRadialGradient(x,y,0,x,y,r);
  g.addColorStop(0,hex(c,a)); g.addColorStop(1,hex(c,0)); ctx.fillStyle=g;
  ctx.beginPath();ctx.arc(x,y,r,0,6.2832);ctx.fill();}

function frame(){
  t+=1; mouse.x+=(tmouse.x-mouse.x)*.05; mouse.y+=(tmouse.y-mouse.y)*.05;
  const px=(mouse.x-.5)*40*DPR, py=(mouse.y-.5)*40*DPR;
  ctx.fillStyle='rgba(5,7,11,.34)';ctx.fillRect(0,0,W,H); // trail
  glow(W*.3+px*1.4,H*.2+py,520*DPR,PAL.cyan,.10);
  glow(W*.78-px,H*.8-py,560*DPR,PAL.violet,.08);
  glow(W*.5+px*.4,H*.5+py*.4,360*DPR,PAL.mint,.07);
  for(const p of parts){p.x+=p.vx;p.y+=p.vy;if(p.x<0)p.x=W;if(p.x>W)p.x=0;if(p.y<0)p.y=H;if(p.y>H)p.y=0;
    ctx.fillStyle=hex('#bbccdd', p.al*.5);ctx.beginPath();ctx.arc(p.x+px*.3,p.y+py*.3,p.r,0,6.28);ctx.fill();}
  const cx=core.x+px, cy=core.y+py;
  for(const n of nodes){
    n.ph+=0.01*n.sp+ n.act*0.04;
    n.x=cx+Math.cos(n.a+Math.sin(n.ph)*.06)*n.rad + Math.sin(t*0.004+n.ph)*8*DPR;
    n.y=cy+Math.sin(n.a+Math.sin(n.ph)*.06)*n.rad + Math.cos(t*0.004+n.ph)*8*DPR;
    n.act*=0.97;
    ctx.strokeStyle=hex(n.col,0.10+n.act*0.5);ctx.lineWidth=(0.6+n.act*1.6)*DPR;
    ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(n.x,n.y);ctx.stroke();
    const tp=(Math.sin(t*0.02*n.sp+n.ph)*.5+.5);
    glow(cx+(n.x-cx)*tp,cy+(n.y-cy)*tp,9*DPR,n.col,.6);
    glow(n.x,n.y,n.r*4,n.col,.4); ctx.fillStyle=hex(n.col,.95);
    ctx.beginPath();ctx.arc(n.x,n.y,n.r*(1+n.act*.4),0,6.28);ctx.fill();
    ctx.fillStyle=hex('#dfe9f5',.55);ctx.font=(11*DPR)+'px -apple-system,Segoe UI,sans-serif';
    ctx.fillText(n.label,n.x+n.r*1.8,n.y+4*DPR);
  }
  core.pa+=0.04; core.act*=0.96;
  const pr=core.r*(1+Math.sin(core.pa)*.06+core.act*.5);
  glow(cx,cy,pr*4.2,PAL.mint,.20);
  glow(cx,cy,pr*2,PAL.cyan,.33);
  ctx.strokeStyle=hex(PAL.mint,.8);ctx.lineWidth=2*DPR;
  ctx.beginPath();ctx.arc(cx,cy,pr,0,6.28);ctx.stroke();
  ctx.strokeStyle=hex('#ffffff',.5+core.act*.5);ctx.lineWidth=1*DPR;
  ctx.beginPath();ctx.arc(cx,cy,pr*0.62,core.pa,core.pa+4.4);ctx.stroke();
  const g=ctx.createRadialGradient(cx,cy,0,cx,cy,pr*.7);
  g.addColorStop(0,hex('#eafff9',.9));g.addColorStop(1,hex(PAL.mint,0));
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,pr*.7,0,6.28);ctx.fill();
  requestAnimationFrame(frame);
}
function spark(label){if(!core)return;core.act=1;
  const n=nodes.find(x=>x.label.toLowerCase().includes((label||'').toLowerCase()));
  if(n)n.act=1; else if(nodes.length)nodes[Math.floor(Math.random()*nodes.length)].act=1;}

/* ====================== DONNÉES RÉELLES ====================== */
const RAIL=[['🧠','Intelligence'],['🌍','Mon monde'],['🧪','Recherche'],['💰','Business'],
  ['🤖','Robotique'],['⌥','Développement'],['⚙️','Système']];
$('#rail').innerHTML=RAIL.map((u,i)=>`<div class="u ${i==0?'on':''}"><span>${u[0]}</span><span class="tip">${u[1]}</span></div>`).join('');

const CHIPS=['Analyse un contrat','Que fait le système ?','Supprime un fichier obsolète','Prépare une RFC','Fais un virement'];
$('#chips').innerHTML=CHIPS.map(c=>`<span class="chip">${c}</span>`).join('');
$$('.chip').forEach(c=>c.onclick=()=>{$('#q').value=c.textContent;send();});

const WORLD=[['PC — RTX','on','prêt'],['Docker','on','3 conteneurs'],['Serveurs','off','à connecter'],
  ['NAS','off','à connecter'],['Robot / Isaac','off','simulation'],['Caméras','off','à connecter']];
$('#world').innerHTML=WORLD.map(w=>`<div class="n"><span class="s ${w[1]}"></span>${w[0]}<em>${w[2]}</em></div>`).join('');
$('#goals').innerHTML=`<div class="g"><div class="r"><b>Construire HELYOS</b><span>82%</span></div><div class="bar"><i style="width:82%"></i></div></div>
  <div class="g"><div class="r"><b>Premier revenu</b><span>15%</span></div><div class="bar"><i style="width:15%"></i></div></div>`;

const hr=new Date().getHours();
$('#greet').firstChild.textContent = (hr<6?'Bonne nuit ':hr<18?'Bonjour ':'Bonsoir ');

let AGENTS=[];
async function boot(){
  try{
    const h=await api('/health'); $('#ver').textContent='v'+h.version;
    AGENTS=await api('/agents');
    seedScene(AGENTS.map(a=>a.name[0].toUpperCase()+a.name.slice(1)));
    renderAgents(); thoughtsLoop(); requestAnimationFrame(frame);
  }catch(e){ $('#state').textContent='hors ligne'; seedScene(['Memory','Planner','Vision','Research']); requestAnimationFrame(frame); }
}
function renderAgents(){
  $('#agents').innerHTML=AGENTS.map(a=>`<div class="ag" data-n="${a.name}">
    <div class="r"><b>${a.name}</b><span class="st">en veille · ${a.required_level}</span></div>
    <div class="bar"><i></i></div></div>`).join('');
}
function workAgent(name,label,pct){
  const el=$(`.ag[data-n="${name}"]`); if(!el)return;
  el.querySelector('.st').textContent=label; el.querySelector('.bar i').style.width=pct+'%';
  spark(name);
  setTimeout(()=>{el.querySelector('.st').textContent='terminé'; },1600);
}
const THINK=['Je relie cette demande au Codex…','La gouvernance valide chaque action avant exécution.',
  'Mémoire : 33 fragments du Codex indexés.','Aucune décision ne reste dans une conversation.',
  'J\'évalue le niveau d\'autonomie requis…','Je trace cette décision dans l\'audit.',
  'Recherche : veille NVIDIA / Isaac en arrière-plan.','Le cœur tourne en local, sans cloud requis.'];
function thoughtsLoop(){const box=$('#thoughts');
  const add=()=>{const d=document.createElement('div');d.className='t';
    d.innerHTML='<b>›</b> '+THINK[Math.floor(Math.random()*THINK.length)];
    box.prepend(d); while(box.children.length>5)box.lastChild.remove();};
  add();setInterval(add,4200);}

/* ====================== CONVERSATION + GOUVERNANCE ====================== */
const MAP=[
  [/supprim|efface|delete|retire/i,'delete','A5'],
  [/écri|ecri|rédige|redige|crée le fichier|cree le fichier|write/i,'write_local','A2'],
  [/mail|e-?mail|envoi|publi|poste|tweet|message/i,'external_sensitive','A2'],
  [/vire|virement|paie|paye|transac|achat|invest|paiement|finance/i,'financial','A5'],
  [/renomme|déplace|deplace/i,'rename_workdir','A3'],
  [/analyse|résume|resume|lis |étudie|etudie|revue|contrat/i,'analyze','A1'],
  [/permission|droits|escalad|privilèg/i,'self_permission','A5'],
];
const ACTNAME={read:'lecture',analyze:'analyse',write_local:'écriture locale',rename_workdir:'renommage',
  delete:'suppression',external_sensitive:'action externe sensible',financial:'transaction financière',self_permission:'changement de permissions'};
const thread=$('#thread'), hero=$('#hero'), stream=$('#stream');
let opened=false;
function openStream(){if(opened)return;opened=true;hero.classList.add('lift');stream.classList.add('show');
  $$('.panel').forEach(p=>{if(p.classList.contains('thoughts')||p.classList.contains('world'))return;});}
function bubble(who,html){const m=document.createElement('div');m.className='msg '+who;
  m.innerHTML=`<div class="av">${who=='u'?'E':'J'}</div><div class="bubble">${html}</div>`;
  thread.appendChild(m);stream.scrollTop=stream.scrollHeight;return m.querySelector('.bubble');}
function detect(q){for(const[re,a,lv]of MAP)if(re.test(q))return{a,lv};return null;}

async function send(){
  const q=$('#q').value.trim(); if(!q)return; $('#q').value='';
  openStream(); bubble('u',q);
  const b=bubble('j','<span class="think"><i></i><i></i><i></i></span>');
  const hit=detect(q);
  spark(hit?hit.a:'research');
  if(AGENTS[0]) workAgent(AGENTS.find(a=>/research|legal|finance/.test(a.name))?.name||AGENTS[0].name,'au travail…',60+Math.random()*35);
  await new Promise(r=>setTimeout(r,650+Math.random()*500));

  if(!hit){
    b.innerHTML=conversational(q); return;
  }
  // action réelle -> gouvernance
  try{
    const v=await api('/intent',{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify({action_type:hit.a,granted_level:hit.lv,description:q,
        has_backup:/sauvegard|backup/i.test(q),validated:/valide|confirme|autorise/i.test(q)})});
    const an=ACTNAME[hit.a]||hit.a;
    let txt;
    if(v.decision=='allow') txt=`D'accord — j'exécute « ${an} ». Niveau ${v.granted_level} suffisant, aucune règle d'or enfreinte.`;
    else if(v.decision=='deny') txt=`Je ne le ferai pas. ${v.reason}`;
    else txt=`Je peux le préparer, mais cette ${an} exige ta validation explicite avant que j'agisse. ${v.reason}`;
    b.innerHTML=`${txt}<div class="v ${v.decision}">${v.decision=='allow'?'✓ autorisé':v.decision=='deny'?'✕ refusé ('+(v.rule||'')+')':'⏸ validation requise '+(v.rule?'('+v.rule+')':'')}</div>`;
  }catch(e){ b.textContent="Le cœur ne répond pas — vérifie que le kernel tourne."; }
}
function conversational(q){
  if(/gouvern|autonom|a0|a5/i.test(q)) return "Mon autonomie est graduée de <b>A0</b> (lecture) à <b>A5</b> (stratégique). Toute action passe par la gouvernance ; je n'agis jamais au-dessus du niveau qui m'est accordé, et je ne peux pas m'auto-promouvoir.";
  if(/qui es|c'est quoi|présente|presente|aide/i.test(q)) return "Je suis l'incarnation de <b>HELYOS</b> — un système d'intelligence gouverné, local d'abord. Demande-moi d'analyser, d'écrire, de chercher ou d'agir : chaque action est tracée et gouvernée.";
  if(/système|systeme|gpu|docker|état|etat|passe/i.test(q)) return "Aperçu de ton monde à droite (connecteurs à venir). Côté cœur : agents en veille, mémoire indexée, gouvernance active. Le vrai modèle d'environnement (PC, GPU, robots) se branche via les ports d'incarnation.";
  return "Bien reçu. Pour l'instant je relie cette demande au Codex et à mes agents. Reformule en action (« analyse… », « écris… », « supprime… ») et tu verras la gouvernance décider en direct.";
}
$('#form').addEventListener('submit',e=>{e.preventDefault();send();});
boot();
</script>
</body>
</html>"""
