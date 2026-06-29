// HELYOS — interface immersive. UI + gouvernance d'abord (sans dépendance),
// puis enrichissement WebGL via import() dynamique (échec WebGL => UI reste OK).

const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const api = async (u, o) => { const r = await fetch(u, o); return r.json(); };
let AGENTS = [], scene3D = null;
let spark = () => {};           // hook vers la scène 3D (remplacé si WebGL OK)

/* ---------------- éléments statiques ---------------- */
const RAIL = [['🧠','Intelligence'],['🌍','Mon monde'],['🧪','Recherche'],['💰','Business'],
  ['🤖','Robotique'],['⌥','Développement'],['⚙️','Système']];
$('#rail').innerHTML = RAIL.map((u,i)=>`<div class="u ${i==0?'on':''}"><span>${u[0]}</span><span class="tip">${u[1]}</span></div>`).join('');
$$('.rail .u').forEach(u=>u.onclick=()=>{$$('.rail .u').forEach(x=>x.classList.remove('on'));u.classList.add('on');});

const CHIPS = ['Analyse un contrat','Que fait le système ?','Supprime un fichier obsolète','Prépare une RFC','Fais un virement'];
$('#chips').innerHTML = CHIPS.map(c=>`<span class="chip">${c}</span>`).join('');
$$('.chip').forEach(c=>c.onclick=()=>{$('#q').value=c.textContent;send();});

const WORLD = [['PC — RTX','on','prêt'],['Docker','on','3 conteneurs'],['Serveurs','off','à connecter'],
  ['NAS','off','à connecter'],['Robot / Isaac','off','simulation'],['Caméras','off','à connecter']];
$('#world').innerHTML = WORLD.map(w=>`<div class="n"><span class="s ${w[1]}"></span>${w[0]}<em>${w[2]}</em></div>`).join('');
$('#goals').innerHTML = `<div class="g"><div class="r"><b>Construire HELYOS</b><span>82%</span></div><div class="bar"><i style="width:82%"></i></div></div>
  <div class="g"><div class="r"><b>Premier revenu</b><span>15%</span></div><div class="bar"><i style="width:15%"></i></div></div>`;

const hr = new Date().getHours();
$('#greet').firstChild.textContent = (hr<6?'Bonne nuit ':hr<18?'Bonjour ':'Bonsoir ');

/* ---------------- données réelles ---------------- */
async function boot(){
  try{
    const h = await api('/health'); $('#ver').textContent = 'v'+h.version;
    AGENTS = await api('/agents'); renderAgents();
    if(scene3D) scene3D.setAgents(AGENTS);
  }catch(e){ $('#state').textContent = 'hors ligne'; }
  thoughtsLoop();
}
function renderAgents(){
  $('#agents').innerHTML = AGENTS.map(a=>`<div class="ag" data-n="${a.name}">
    <div class="r"><b>${a.name}</b><span class="st">en veille · ${a.required_level}</span></div>
    <div class="bar"><i></i></div></div>`).join('');
}
function workAgent(name,label,pct){
  const el = $(`.ag[data-n="${name}"]`); if(!el) return;
  el.querySelector('.st').textContent = label; el.querySelector('.bar i').style.width = pct+'%';
  spark(name);
  setTimeout(()=>{ el.querySelector('.st').textContent='terminé'; }, 1700);
}
const THINK = ['Je relie cette demande au Codex…','La gouvernance valide chaque action avant exécution.',
  'Mémoire : 33 fragments du Codex indexés.','Aucune décision ne reste dans une conversation.',
  'J\'évalue le niveau d\'autonomie requis…','Je trace cette décision dans l\'audit.',
  'Veille NVIDIA / Isaac en arrière-plan.','Le cœur tourne en local, sans cloud requis.'];
function thoughtsLoop(){
  const box = $('#thoughts');
  const add = ()=>{ const d=document.createElement('div'); d.className='t';
    d.innerHTML='<b>›</b> '+THINK[Math.floor(Math.random()*THINK.length)];
    box.prepend(d); while(box.children.length>5) box.lastChild.remove(); };
  add(); setInterval(add, 4200);
}

/* ---------------- conversation + gouvernance ---------------- */
const MAP = [
  [/supprim|efface|delete|retire/i,'delete','A5'],
  [/écri|ecri|rédige|redige|crée le fichier|cree le fichier|write/i,'write_local','A2'],
  [/mail|e-?mail|envoi|publi|poste|tweet|message/i,'external_sensitive','A2'],
  [/vire|virement|paie|paye|transac|achat|invest|paiement|finance/i,'financial','A5'],
  [/renomme|déplace|deplace/i,'rename_workdir','A3'],
  [/analyse|résume|resume|lis |étudie|etudie|revue|contrat/i,'analyze','A1'],
  [/permission|droits|escalad|privilèg/i,'self_permission','A5'],
];
const ACTNAME = {read:'lecture',analyze:'analyse',write_local:'écriture locale',rename_workdir:'renommage',
  delete:'suppression',external_sensitive:'action externe sensible',financial:'transaction financière',self_permission:'changement de permissions'};
const thread=$('#thread'), hero=$('#hero'), stream=$('#stream');
let opened=false;
function openStream(){ if(opened) return; opened=true; hero.classList.add('lift'); stream.classList.add('show'); }
function bubble(who,html){ const m=document.createElement('div'); m.className='msg '+who;
  m.innerHTML=`<div class="av">${who=='u'?'E':'J'}</div><div class="bubble">${html}</div>`;
  thread.appendChild(m); stream.scrollTop=stream.scrollHeight; return m.querySelector('.bubble'); }
function detect(q){ for(const[re,a,lv] of MAP) if(re.test(q)) return {a,lv}; return null; }

async function send(){
  const q=$('#q').value.trim(); if(!q) return; $('#q').value='';
  openStream(); bubble('u',q);
  const b=bubble('j','<span class="think"><i></i><i></i><i></i></span>');
  const hit=detect(q); spark(hit?hit.a:'research');
  const w = AGENTS.find(a=>/research|legal|finance/.test(a.name)) || AGENTS[0];
  if(w) workAgent(w.name,'au travail…',60+Math.random()*35);
  await new Promise(r=>setTimeout(r,650+Math.random()*500));
  if(!hit){ b.innerHTML=conversational(q); return; }
  try{
    const v=await api('/intent',{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify({action_type:hit.a,granted_level:hit.lv,description:q,
        has_backup:/sauvegard|backup/i.test(q), validated:/valide|confirme|autorise/i.test(q)})});
    const an=ACTNAME[hit.a]||hit.a; let txt;
    if(v.decision=='allow') txt=`D'accord — j'exécute « ${an} ». Niveau ${v.granted_level} suffisant, aucune règle d'or enfreinte.`;
    else if(v.decision=='deny') txt=`Je ne le ferai pas. ${v.reason}`;
    else txt=`Je peux le préparer, mais cette ${an} exige ta validation avant que j'agisse. ${v.reason}`;
    const tag = v.decision=='allow'?'✓ autorisé':v.decision=='deny'?('✕ refusé '+(v.rule?'('+v.rule+')':'')):('⏸ validation requise '+(v.rule?'('+v.rule+')':''));
    b.innerHTML=`${txt}<div class="v ${v.decision}">${tag}</div>`;
  }catch(e){ b.textContent='Le cœur ne répond pas — vérifie que le kernel tourne.'; }
}
function conversational(q){
  if(/gouvern|autonom|a0|a5/i.test(q)) return "Mon autonomie est graduée de <b>A0</b> (lecture) à <b>A5</b> (stratégique). Toute action passe par la gouvernance ; je n'agis jamais au-dessus du niveau accordé et je ne peux pas m'auto-promouvoir.";
  if(/qui es|c'est quoi|présente|presente|aide|bonjour|salut/i.test(q)) return "Je suis l'incarnation d'<b>HELYOS</b> — une intelligence gouvernée, locale d'abord. Demande-moi d'analyser, d'écrire, de chercher ou d'agir : chaque action est tracée et gouvernée.";
  if(/système|systeme|gpu|docker|état|etat|passe|fait/i.test(q)) return "Aperçu de ton monde à droite (connecteurs à venir). Côté cœur : agents en veille, mémoire indexée, gouvernance active. Le vrai modèle d'environnement (PC, GPU, robots) se branchera via les ports d'incarnation.";
  return "Bien reçu. Reformule en action (« analyse… », « écris… », « supprime… », « vire… ») et tu verras la gouvernance décider en direct.";
}
$('#form').addEventListener('submit', e=>{ e.preventDefault(); send(); });

/* ---------------- scène WebGL (enrichissement) ---------------- */
function makeRadialTex(THREE, inner){
  const c=document.createElement('canvas'); c.width=c.height=128; const g=c.getContext('2d');
  const grd=g.createRadialGradient(64,64,0,64,64,64);
  grd.addColorStop(0,'rgba(255,255,255,1)'); grd.addColorStop(inner,'rgba(255,255,255,.5)');
  grd.addColorStop(1,'rgba(255,255,255,0)'); g.fillStyle=grd; g.fillRect(0,0,128,128);
  const t=new THREE.CanvasTexture(c); return t;
}
function init3D(THREE){
  const COLORS=[0x6ff7d6,0x49b6ff,0xb69bff,0xffce6a];
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
  renderer.setSize(innerWidth,innerHeight);
  $('#scene').appendChild(renderer.domElement);
  const scene=new THREE.Scene(); scene.fog=new THREE.FogExp2(0x04060a,0.018);
  const camera=new THREE.PerspectiveCamera(52,innerWidth/innerHeight,0.1,300); camera.position.set(0,0,19);

  const glow=makeRadialTex(THREE,.25), dot=makeRadialTex(THREE,.5);
  const sprite=(color,scale,tex)=>{ const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex||glow,color,
    transparent:true,blending:THREE.AdditiveBlending,depthWrite:false})); s.scale.set(scale,scale,1); return s; };

  // coeur
  const core=new THREE.Group();
  const ico=new THREE.Mesh(new THREE.IcosahedronGeometry(2.7,1),
    new THREE.MeshBasicMaterial({color:0x6ff7d6,wireframe:true,transparent:true,opacity:.5}));
  const shell=new THREE.Mesh(new THREE.IcosahedronGeometry(1.8,2),
    new THREE.MeshBasicMaterial({color:0x123a33,transparent:true,opacity:.55}));
  core.add(sprite(0x6ff7d6,16),sprite(0xeafff9,5),shell,ico); scene.add(core);
  let coreAct=0, t=0;

  // particules
  const N=1700, pos=new Float32Array(N*3);
  for(let i=0;i<N;i++){ const r=10+Math.random()*30, th=Math.random()*6.283, ph=Math.acos(2*Math.random()-1);
    pos[i*3]=r*Math.sin(ph)*Math.cos(th); pos[i*3+1]=r*Math.sin(ph)*Math.sin(th)*.6; pos[i*3+2]=r*Math.cos(ph); }
  const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.BufferAttribute(pos,3));
  const stars=new THREE.Points(pg,new THREE.PointsMaterial({size:.16,map:dot,color:0x9fc7ff,
    transparent:true,opacity:.55,blending:THREE.AdditiveBlending,depthWrite:false})); scene.add(stars);

  // agents (noeuds + arêtes)
  let nodes=[];
  function setAgents(list){
    nodes.forEach(n=>{scene.remove(n.g);scene.remove(n.line);});
    nodes=list.map((a,i)=>{
      const col=COLORS[i%4], g=new THREE.Group();
      g.add(sprite(col,1.7), sprite(0xffffff,.6,dot)); scene.add(g);
      const lp=new Float32Array(6); const lg=new THREE.BufferGeometry();
      lg.setAttribute('position',new THREE.BufferAttribute(lp,3));
      const line=new THREE.Line(lg,new THREE.LineBasicMaterial({color:col,transparent:true,opacity:.2,
        blending:THREE.AdditiveBlending,depthWrite:false})); scene.add(line);
      return {name:a.name,col,g,line,lp,a:(i/list.length)*6.283,r:6.6+Math.random()*1.6,
        yb:(Math.random()-.5)*3,sp:.12+Math.random()*.12,ph:Math.random()*6.283,act:0};
    });
  }

  const mouse={x:0,y:0}, target={x:0,y:0};
  addEventListener('pointermove',e=>{ target.x=(e.clientX/innerWidth-.5); target.y=(e.clientY/innerHeight-.5); });
  addEventListener('resize',()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth,innerHeight); });

  function loop(){
    t+=0.01; coreAct*=0.96;
    core.rotation.y+=0.0016; core.rotation.x=Math.sin(t*.3)*0.12;
    const br=1+Math.sin(t*1.2)*0.03+coreAct*0.35; core.scale.setScalar(br);
    ico.rotation.y-=0.004; ico.rotation.z+=0.002;
    stars.rotation.y+=0.0004;
    for(const n of nodes){
      n.act*=0.95; const ang=n.a+t*n.sp;
      const x=Math.cos(ang)*n.r, z=Math.sin(ang)*n.r, y=n.yb+Math.sin(t*1.4+n.ph)*0.7;
      n.g.position.set(x,y,z);
      const hs=1.7+n.act*2.2; n.g.children[0].scale.set(hs,hs,1);
      n.lp[3]=x; n.lp[4]=y; n.lp[5]=z; n.line.geometry.attributes.position.needsUpdate=true;
      n.line.material.opacity=0.12+(Math.sin(t*2+n.ph)*.5+.5)*0.16+n.act*0.5;
    }
    mouse.x+=(target.x-mouse.x)*0.05; mouse.y+=(target.y-mouse.y)*0.05;
    camera.position.x=mouse.x*4.5; camera.position.y=-mouse.y*3; camera.lookAt(0,0,0);
    renderer.render(scene,camera); requestAnimationFrame(loop);
  }
  loop();
  return {
    setAgents,
    spark(name){ coreAct=1; const n=nodes.find(x=>x.name && (name||'').toLowerCase().includes(x.name.toLowerCase()));
      if(n) n.act=1; else if(nodes.length) nodes[Math.floor(Math.random()*nodes.length)].act=1; }
  };
}

/* ---------------- démarrage ---------------- */
boot();
import('three').then(THREE=>{
  try{ scene3D=init3D(THREE); spark=(n)=>scene3D.spark(n); if(AGENTS.length) scene3D.setAgents(AGENTS); }
  catch(e){ console.warn('WebGL init échec:',e); }
}).catch(e=>{ console.warn('Three.js indisponible — fond CSS conservé.',e); });
