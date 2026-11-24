/* Maternacare AI PWA — browser controller. All data in localStorage. */
let LANG = localStorage.getItem('mc_lang') || 'en';
let P = JSON.parse(localStorage.getItem('mc_profile') || 'null');
let TASKS = JSON.parse(localStorage.getItem('mc_tasks') || '[]');
let CHAT = JSON.parse(localStorage.getItem('mc_chat') || '[]');
let deferredPrompt = null;

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const tr = k => Engine.t(LANG, k);
const save = () => {
  localStorage.setItem('mc_profile', JSON.stringify(P));
  localStorage.setItem('mc_tasks', JSON.stringify(TASKS));
  localStorage.setItem('mc_chat', JSON.stringify(CHAT));
};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function applyLang() {
  document.documentElement.lang = LANG;
  $('#lang').value = LANG; $('#sLang').value = LANG;
  $$('[data-i18n]').forEach(el => el.textContent = tr(el.dataset.i18n));
  $$('[data-ph]').forEach(el => el.placeholder = tr(el.dataset.ph));
  $('#disclaimerText').textContent = tr('disclaimer');
  $('#emerBanner').textContent = tr('emergency_banner');
  $('#emerLine').textContent = tr('call102');
  $('#foot').textContent = tr('footer_note');
  if ($('#gatePlans')) $('#gatePlans').innerHTML = planHTML();
  if (P) { renderAll(); renderSubPage(); }
}

const GATED = ['learn','trad','calendar','chat'];
function go(tab) {
  if (GATED.includes(tab) && P && !Payments.isSubscribed()) { showGate(); return; }
  $$('.page').forEach(p => p.classList.add('hidden'));
  const el = $('#' + tab); if (el) el.classList.remove('hidden');
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  window.scrollTo({top: 0, behavior: 'smooth'});
  if (tab === 'chat') renderChat();
  if (tab === 'sub') renderSubPage();
}

function planHTML(){
  return Payments.PAY_CONFIG.plans.map(p=>`<div class="plan" onclick="startPay('${p.id}')">
    <div><b>${esc(p.label)}</b><small>${Payments.PAY_CONFIG.currency} ${p.price.toLocaleString('en-IN')}</small></div>
    <div class="amt">₹${p.price.toLocaleString('en-IN')}</div></div>`).join('');
}
function showGate(){
  $('#gatePlans').innerHTML=planHTML();
  $('#gate').style.display='grid';
}
window.startPay = id => {
  Payments.openCheckout(id, paymentId=>{
    Payments.activateSubscription(id, paymentId);
    $('#gate').style.display='none';
    alert(tr('payment_success'));
    renderAll();
  }, msg=>{ alert(tr('payment_failed')+'\n'+msg); });
};
function renderSubPage(){
  const ok=Payments.isSubscribed(), s=Payments.getSubscription();
  const status=$('#subStatus');
  if(ok){
    status.className='sub-status active';
    status.innerHTML=`<h2>${esc(tr('subscribed'))}</h2><div class="big">${esc(tr('plan'))}: ${esc(s.plan)}</div><p class="muted">${esc(tr('active_until'))}: ${new Date(s.expiresAt).toLocaleDateString()} · ${Payments.daysLeft()} ${esc(tr('days_left'))}</p>`;
  } else {
    status.className='sub-status';
    status.innerHTML=`<h2>${esc(tr('not_subscribed'))}</h2><p class="muted">${esc(tr('sub_desc'))}</p><div class="plans" style="margin-top:12px">${planHTML()}</div>`;
  }
  $('#deviceIdText').textContent=Payments.getDeviceId();
}
$('#gateClose').addEventListener('click', ()=>$('#gate').style.display='none');
$('#resetSub').addEventListener('click', ()=>{ if(confirm(tr('clear')+'?')){ Payments.clearSubscription(); renderSubPage(); } });
$$('.tab, [data-tab]').forEach(b => b.addEventListener('click', e => {
  e.preventDefault();
  const tab = b.dataset.tab;
  if (tab === 'home' && !P) { go('onboarding'); return; }
  go(tab);
}));
$('#lang').addEventListener('change', e => { LANG = e.target.value; localStorage.setItem('mc_lang', LANG); applyLang(); });
$('#sLang').addEventListener('change', e => { LANG = e.target.value; localStorage.setItem('mc_lang', LANG); applyLang(); });
$('#sStage').addEventListener('change', e => { $('#pregFields').style.display = e.target.value === 'pregnant' ? 'block' : 'none'; });

$('#setup').addEventListener('submit', e => {
  e.preventDefault();
  if (!$('#sConsent').checked) { alert(tr('consent_required')); return; }
  const raw = $('#sStage').value;
  const stage = raw === 'pregnant' ? 'pregnancy' : raw;
  const lmp = $('#sLmp').value || null, edd = $('#sEdd').value || null, weeks = $('#sWeeks').value || null;
  const c = Engine.eddFrom({lmp, edd, weeks: weeks ? +weeks : null});
  P = {
    language: LANG, stage, lmp, edd, weeks: weeks ? +weeks : null,
    computed_edd: c.edd ? c.edd.toISOString().slice(0, 10) : null, days: c.days,
    first: $('#sFirst').checked, risk: $('#sRisk').checked,
    conditions: $('#sCond').value, medicines: $('#sMed').value, allergies: $('#sAllergy').value,
    doctor: $('#sDoc').value, emergency: $('#sEmer').value,
  };
  // Generate guidance tasks once.
  if (!TASKS.length) {
    const items = Engine.ancSchedule({edd: P.computed_edd});
    if (P.stage === 'pregnancy') TASKS = items;
  }
  save(); renderAll();
  if (!Payments.isSubscribed()) showGate(); else go('home');
});
$('#clear').addEventListener('click', () => {
  if (!confirm(tr('clear') + '?')) return;
  localStorage.removeItem('mc_profile'); localStorage.removeItem('mc_tasks'); localStorage.removeItem('mc_chat');
  P = null; TASKS = []; CHAT = []; go('onboarding');
});

function runTriage(text, out) {
  if (!text.trim()) return;
  const stage = P?.stage || 'pregnancy';
  const a = Engine.triage(text, stage);
  if (!a) { out.innerHTML = `<div class="result ok"><b>✓</b>${esc(tr('no_answer'))}</div>`; return; }
  const cls = a.urgency === 'emergency' ? 'em' : 'ur';
  const label = a.urgency === 'emergency' ? '🚨 ' + tr('open_emergency') : '⚠️';
  const reason = (a.reason[LANG] || a.reason.en), action = (a.action[LANG] || a.action.en);
  out.innerHTML = `<div class="result ${cls}"><b>${esc(label)}</b><p>${esc(reason)}</p><p><b>${esc(action)}</b></p><ul>${a.steps.map(s=>`<li>${esc(s)}</li>`).join('')}</ul><p class="muted" style="margin-top:10px">${esc(tr('call102'))}</p></div>`;
}
$('#quickF').addEventListener('submit', e => { e.preventDefault(); runTriage($('#quickIn').value, $('#quickOut')); $('#quickIn').value = ''; });
$('#safetyF').addEventListener('submit', e => { e.preventDefault(); runTriage($('#safetyIn').value, $('#safetyOut')); $('#safetyIn').value = ''; });

$('#addBtn').addEventListener('click', () => {
  const title = $('#newTask').value.trim(), due = $('#newDue').value;
  if (!title || !due) { alert(tr('task_name')); return; }
  TASKS.push({id:'custom_'+Date.now(),type:'custom',title,due,done:false,custom:true});
  TASKS.sort((a,b)=>a.due.localeCompare(b.due));
  $('#newTask').value=''; $('#newDue').value=''; save(); renderTasks(); renderHome();
});
function toggleTask(id){ const x=TASKS.find(t=>t.id===id); if(x){x.done=!x.done;save();renderTasks();renderHome();} }
function delTask(id){ TASKS=TASKS.filter(t=>t.id!==id); save(); renderTasks(); renderHome(); }
window.toggleTask=toggleTask; window.delTask=delTask;

$('#tradSearch').addEventListener('input', renderTrad);

$('#chatF').addEventListener('submit', e => {
  e.preventDefault();
  const text = $('#chatIn').value.trim(); if(!text) return;
  $('#chatIn').value='';
  CHAT.push({role:'user',text});
  const r = Engine.chatReply(text, P || {stage:'pregnancy'}, TASKS, LANG);
  CHAT.push({role:'assistant',text:r.text,kind:r.kind});
  save(); renderChat();
});
$('#feedbackBtn').addEventListener('click', ()=>$('#feedbackModal').style.display='flex');
$('#fbCancel').addEventListener('click', ()=>$('#feedbackModal').style.display='none');
$('#fbSend').addEventListener('click', ()=>{
  const t=$('#fbText').value.trim(); if(!t)return;
  const arr=JSON.parse(localStorage.getItem('mc_feedback')||'[]'); arr.push({text:t,at:new Date().toISOString()});
  localStorage.setItem('mc_feedback',JSON.stringify(arr));
  $('#fbText').value=''; $('#feedbackModal').style.display='none'; alert(tr('feedback_saved'));
});

function renderChat(){
  const log=$('#log'); log.innerHTML='';
  CHAT.forEach(m=>{
    const d=document.createElement('div');
    d.className='msg '+m.role+(m.kind==='danger'?' danger':'');
    d.innerHTML=`<small>${m.role==='user'?tr('you'):tr('assistant')}</small>${esc(m.text)}`;
    log.appendChild(d);
  });
  log.scrollTop=log.scrollHeight;
}
function renderTrad(){
  const q=$('#tradSearch').value.toLowerCase().trim();
  const items=Engine.TRADITIONS.filter(x=>!q||x.name.toLowerCase().includes(q)||x.key.toLowerCase().includes(q));
  $('#tradList').innerHTML=items.map((x,i)=>{
    const v=Engine.VERDICT[x.verdict]||Engine.VERDICT.insufficient;
    return `<div class="trad"><div class="trad-h" onclick="tog(${i})"><h3>${esc(x.name)}</h3><span class="badge ${x.verdict}">${esc(v[{en:0,hi:1,bn:2}[LANG]])}</span></div>
    <div class="trad-b" id="tb${i}"><div class="trow"><b>${tr('belief')}</b><p>${esc(x.belief)}</p></div><div class="trow"><b>${tr('why')}</b><p>${esc(x.why)}</p></div>
    <div class="trow"><b>${tr('evidence')}</b><p>${esc(x.evidence)}</p></div><div class="trow"><b>${tr('benefit')}</b><p>${esc(x.benefit)}</p></div>
    <div class="trow"><b>${tr('risk')}</b><p>${esc(x.risk)}</p></div><div class="trow"><b>${tr('verdict')}</b><p>${esc(v[{en:0,hi:1,bn:2}[LANG]])}</p></div>
    <div class="trow"><b>${tr('alternative')}</b><p>${esc(x.alternative)}</p></div><div class="trow doc"><b>${tr('when_doctor')}</b><p>${esc(x.doctor)}</p></div>
    <div class="trow"><b>${tr('sources')}</b><p class="muted">${esc(x.source)}</p></div></div></div>`;
  }).join('');
}
window.tog=i=>$('#tb'+i).classList.toggle('open');

function eduHTML(items){
  if(!items||!items.length) return `<p class="empty">${esc(tr('education_none'))}</p>`;
  return items.map(it=>`<div class="edu-item"><h3>${esc(it.title[LANG]||it.title.en)}</h3><p>${esc(it.body[LANG]||it.body.en)}</p><div class="src">${esc(it.source)}</div></div>`).join('');
}
function renderTasks(){
  const list=$('#taskList');
  if(!TASKS.length){list.innerHTML=`<p class="empty">${esc(tr('all_done'))}</p>`;return;}
  const today=new Date().toISOString().slice(0,10);
  list.innerHTML=TASKS.map(x=>{
    const status=x.done?'done':x.due<today?'overdue':'upcoming';
    return `<div class="task"><button class="tk ${x.done?'done':''}" onclick="toggleTask('${x.id}')">${x.done?'✓':''}</button>
      <div class="tm"><div class="tt ${x.done?'done':''}">${esc(x.title)}</div><div class="tmeta"><span class="pill ${status}">${esc(tr(status))}</span><span>${esc(x.due)}</span>${x.week?`<span>${tr('week')} ${x.week}</span>`:''}</div></div>
      ${x.custom?`<button class="tdel" onclick="delTask('${x.id}')">×</button>`:''}</div>`;
  }).join('');
}
function renderHome(){
  if(!P)return;
  const stage=P.stage, days=P.days, week=Math.floor((days||0)/7);
  const k=Engine.stageKey(P);
  const triKey={t1:'trimester_1',t2:'trimester_2',t3:'trimester_3'}[k]||k;
  $('#hStage').textContent=stage==='pregnancy'?(tr(triKey)):tr(stage==='postpartum'?'stage_postpartum_s':'stage_baby_s');
  $('#hWeek').textContent=stage==='pregnancy'?`${tr('week')} ${week}`:tr(stage==='postpartum'?'stage_postpartum_s':'stage_baby_s');
  $('#hTri').textContent=stage==='pregnancy'?`${week} / 40`:'';
  $('#hEdd').textContent=P.computed_edd||tr('not_set');
  const subOk=Payments.isSubscribed();
  $('#subChipText').textContent=subOk?`${tr('subscribed')} · ${Payments.daysLeft()} ${tr('days_left')}`:tr('subscribe');
  $('#subChipText').className=subOk?'on':'';
  const open=TASKS.filter(x=>!x.done).sort((a,b)=>a.due.localeCompare(b.due));
  $('#hNext').textContent=open.length?open[0].title+' · '+open[0].due:tr('all_done');
  const pct=stage==='pregnancy'?Math.min(100,Math.round(week/40*100)):100;
  $('#hPct').textContent=pct+'%';
  $('#hRing').style.background=`conic-gradient(#ffd98a ${pct}%, rgba(255,255,255,.25) 0)`;
  $('#homeEdu').innerHTML=eduHTML(Engine.educationFor(P).slice(0,2));
  $('#homeTasks').innerHTML=open.length?open.slice(0,3).map(x=>`<div class="task"><div class="tm"><div class="tt">${esc(x.title)}</div><div class="tmeta"><span>${esc(x.due)}</span></div></div></div>`).join(''):`<p class="empty">${esc(tr('all_done'))}</p>`;
}
function renderAll(){
  renderHome(); renderTasks(); renderTrad(); renderChat();
  const items=Engine.educationFor(P||{stage:'pregnancy'});
  $('#eduList').innerHTML=eduHTML(items);
  $('#learnLine').textContent=P&&P.stage==='pregnancy'?`${tr('week')} ${Math.floor((P.days||0)/7)}`:'';
}

// PWA install
window.addEventListener('beforeinstallprompt', e=>{ e.preventDefault(); deferredPrompt=e; const b=$('#installBtn'); if(b) b.hidden=false; });
$('#installBtn').addEventListener('click', async ()=>{ if(!deferredPrompt)return; deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt=null; $('#installBtn').hidden=true; });

// Service worker
if('serviceWorker' in navigator) window.addEventListener('load', ()=> navigator.serviceWorker.register('sw.js').catch(()=>{}));

(async function init(){
  applyLang();
  if(P && P.language && P.language!==LANG){ LANG=P.language; localStorage.setItem('mc_lang',LANG); applyLang(); }
  if(P){ renderAll(); go('home'); }
  else { $('#pregFields').style.display='block'; go('onboarding'); }
})();
