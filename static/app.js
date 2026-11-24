// Maternacare AI MVP — front-end controller.
// Safety rule: danger-sign results are rendered as urgent alerts, never softened.

let LANG = localStorage.getItem('mc_lang') || 'en';
let DICT = {};
let STATE = { profile: null, tasks: [], summary: null };
let currentTab = 'home';
let tradOpen = null;

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];

function tr(key) { return DICT[key] || key; }

function applyLang() {
  document.documentElement.lang = LANG;
  $('#langSelect').value = LANG;
  $('#setupLang').value = LANG;
  $$('[data-i18n]').forEach(el => { el.textContent = tr(el.dataset.i18n); });
  $$('[data-i18n-ph]').forEach(el => { el.placeholder = tr(el.dataset.i18nPh); });
  $('#disclaimerText').textContent = tr('disclaimer');
  $('#emergencyBanner').textContent = tr('emergency_banner');
  $('#callLine').textContent = tr('call102');
  $('#footerNote').textContent = tr('footer_note');
  if (STATE.profile) renderAll();
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    let msg = 'Request failed';
    try { msg = (await res.json()).error || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function go(tab) {
  currentTab = tab;
  $$('.page').forEach(p => p.classList.add('hidden'));
  const page = $('#' + tab);
  if (page) page.classList.remove('hidden');
  $$('.tab').forEach(b => b.classList.toggle('tab--active', b.dataset.tab === tab));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

$$('.tab').forEach(b => b.addEventListener('click', () => {
  const tab = b.dataset.tab;
  if (tab === 'home' && !STATE.profile) { go('onboarding'); return; }
  go(tab);
  if (tab === 'chat') loadChat();
}));
$$('[data-tab]').forEach(b => b.addEventListener('click', e => {
  e.preventDefault();
  const tab = b.dataset.tab;
  if (tab === 'home' && !STATE.profile) { go('onboarding'); return; }
  go(tab);
  if (tab === 'chat') loadChat();
}));

$('#langSelect').addEventListener('change', async e => {
  LANG = e.target.value;
  localStorage.setItem('mc_lang', LANG);
  DICT = await api('/api/strings?lang=' + LANG);
  applyLang();
});
$('#setupLang').addEventListener('change', async e => {
  LANG = e.target.value;
  localStorage.setItem('mc_lang', LANG);
  DICT = await api('/api/strings?lang=' + LANG);
  applyLang();
});

$('#stage').addEventListener('change', e => {
  $('#pregnancyFields').style.display = e.target.value === 'pregnant' ? 'block' : 'none';
});

$('#setupForm').addEventListener('submit', async e => {
  e.preventDefault();
  const f = new FormData(e.target);
  const stageVal = f.get('stage');
  const stage = stageVal === 'pregnant' ? 'pregnancy' : stageVal;
  const data = {
    language: LANG,
    consent: $('#consent').checked,
    stage,
    lmp: f.get('lmp') || null,
    edd: f.get('edd') || null,
    weeks: f.get('weeks') || null,
    first_pregnancy: $('#firstPreg').checked,
    high_risk: $('#highRisk').checked,
    conditions: f.get('conditions') || '',
    medicines: f.get('medicines') || '',
    allergies: f.get('allergies') || '',
    doctor: f.get('doctor') || '',
    emergency_contact: f.get('emergency_contact') || '',
  };
  try {
    const res = await api('/api/profile', { method: 'POST', body: JSON.stringify(data) });
    STATE.profile = res.profile;
    STATE.tasks = res.tasks;
    await refresh();
    go('home');
  } catch (err) { alert(err.message); }
});

$('#clearBtn').addEventListener('click', async () => {
  if (!confirm(tr('logout') + '?')) return;
  await api('/api/profile', { method: 'DELETE' });
  STATE = { profile: null, tasks: [], summary: null };
  go('onboarding');
});

$('#quickForm').addEventListener('submit', e => { e.preventDefault(); runTriage('#quickText', '#quickResult'); });
$('#safetyForm').addEventListener('submit', e => { e.preventDefault(); runTriage('#safetyText', '#safetyResult'); });

async function runTriage(inputSel, outSel) {
  const text = $(inputSel).value.trim();
  if (!text) return;
  const res = await api('/api/triage', { method: 'POST', body: JSON.stringify({ text, language: LANG }) });
  const box = $(outSel);
  if (!res.alert) {
    box.innerHTML = `<div class="result result--safe"><strong>✓</strong>${esc(res.message)}</div>`;
    return;
  }
  const cls = res.urgency === 'emergency' ? 'result--emergency' : 'result--urgent';
  const label = res.urgency === 'emergency' ? '🚨 ' + tr('open_emergency') : '⚠️';
  box.innerHTML = `<div class="result ${cls}">
    <strong>${label}</strong>
    <p>${esc(res.reason)}</p>
    <p><b>${esc(res.action)}</b></p>
    <ul>${res.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
    <p class="muted" style="margin-top:10px">${esc(res.emergency_line)}</p>
  </div>`;
}

$('#addTaskBtn').addEventListener('click', async () => {
  const title = $('#newTaskName').value.trim();
  const due = $('#newTaskDue').value;
  if (!title || !due) { alert(tr('task_name') + ' + ' + tr('due_date')); return; }
  const res = await api('/api/tasks', { method: 'POST', body: JSON.stringify({ title, due, type: 'custom' }) });
  STATE.tasks = res.tasks;
  $('#newTaskName').value = ''; $('#newTaskDue').value = '';
  renderTasks();
});

$('#tradSearch').addEventListener('input', () => loadTraditions());
$('#chatForm').addEventListener('submit', async e => {
  e.preventDefault();
  const input = $('#chatInput');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  appendMsg('user', text);
  try {
    const res = await api('/api/chat', { method: 'POST', body: JSON.stringify({ text, language: LANG }) });
    appendMsg('assistant', res.reply, res.kind);
  } catch (err) { appendMsg('assistant', err.message); }
});

$('#sendFeedback').addEventListener('click', async () => {
  const text = $('#feedbackText').value.trim();
  if (!text) return;
  await api('/api/feedback', { method: 'POST', body: JSON.stringify({ text }) });
  $('#feedbackText').value = '';
  $('#feedbackModal').style.display = 'none';
  alert(tr('feedback_saved'));
});

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function appendMsg(role, text, kind = '') {
  const log = $('#chatLog');
  const div = document.createElement('div');
  div.className = 'msg msg--' + role + (kind === 'danger' ? ' msg--danger' : '');
  div.innerHTML = `<small>${role === 'user' ? tr('you') : tr('assistant')}</small>${esc(text)}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function loadChat() {
  const log = $('#chatLog');
  log.innerHTML = '';
  const history = await api('/api/chat');
  history.forEach(m => appendMsg(m.role, m.text, m.kind));
}

async function loadTraditions() {
  const q = $('#tradSearch').value.trim();
  const items = await api('/api/traditions?lang=' + LANG + '&q=' + encodeURIComponent(q));
  const list = $('#tradList');
  if (!items.length) { list.innerHTML = `<p class="empty">${esc(tr('no_answer'))}</p>`; return; }
  list.innerHTML = items.map((it, i) => {
    const key = it.verdict_key;
    const badge = ['safe', 'insufficient', 'harmful', 'contraindicated'].includes(key) ? key : 'insufficient';
    return `<div class="trad-item">
      <div class="trad-item__head" onclick="toggleTrad(${i})">
        <h3>${esc(it.name)}</h3><span class="badge badge--${badge}">${esc(it.verdict)}</span>
      </div>
      <div class="trad-item__body" id="tradBody${i}">
        <div class="trow"><b>${tr('belief')}</b><p>${esc(it.belief)}</p></div>
        <div class="trow"><b>${tr('why')}</b><p>${esc(it.why)}</p></div>
        <div class="trow"><b>${tr('evidence')}</b><p>${esc(it.evidence)}</p></div>
        <div class="trow"><b>${tr('benefit')}</b><p>${esc(it.benefit)}</p></div>
        <div class="trow"><b>${tr('risk')}</b><p>${esc(it.risk)}</p></div>
        <div class="trow"><b>${tr('verdict')}</b><p>${esc(it.verdict)}</p></div>
        <div class="trow"><b>${tr('alternative')}</b><p>${esc(it.alternative)}</p></div>
        <div class="trow doctor"><b>${tr('when_doctor')}</b><p>${esc(it.doctor)}</p></div>
        <div class="trow"><b>${tr('sources')}</b><p class="muted">${esc(it.source)}</p></div>
      </div>
    </div>`;
  }).join('');
}

window.toggleTrad = i => {
  const body = $('#tradBody' + i);
  body.classList.toggle('open');
};

function renderTasks() {
  const list = $('#taskList');
  if (!STATE.tasks.length) { list.innerHTML = `<p class="empty">${esc(tr('all_done'))}</p>`; return; }
  list.innerHTML = STATE.tasks.map(t => {
    const title = t.title[LANG] || t.title.en;
    const note = t.note ? (t.note[LANG] || t.note.en) : '';
    const pillCls = t.status === 'done' ? 'done' : t.status;
    const pillLabel = tr(t.status);
    return `<div class="task">
      <button class="task__check ${t.done ? 'task__check--done' : ''}" onclick="toggleTask('${t.id}')">${t.done ? '✓' : ''}</button>
      <div class="task__main">
        <div class="task__title ${t.done ? 'task__title--done' : ''}">${esc(title)}</div>
        <div class="task__meta"><span class="pill pill--${pillCls}">${pillLabel}</span><span>${esc(t.due)}</span>${t.week ? `<span>${tr('week')} ${t.week}</span>` : ''}</div>
        ${note ? `<div class="task__note">${esc(note)}</div>` : ''}
      </div>
      ${t.custom ? `<button class="task__del" onclick="delTask('${t.id}')" title="${tr('remove')}">×</button>` : ''}
    </div>`;
  }).join('');
}

window.toggleTask = async id => {
  const res = await api(`/api/tasks/${id}/done`, { method: 'POST' });
  STATE.tasks = res.tasks;
  renderTasks();
  await refreshSummary();
};

window.delTask = async id => {
  const res = await api('/api/tasks/' + id, { method: 'DELETE' });
  STATE.tasks = res.tasks;
  renderTasks();
  await refreshSummary();
};

function renderEducation(items, container) {
  if (!items.length) { container.innerHTML = `<p class="empty">${esc(tr('education_none'))}</p>`; return; }
  container.innerHTML = items.map(it => `<div class="edu-item">
    <h3>${esc(it.title)}</h3><p>${esc(it.body)}</p>
    <div class="source">${esc(it.source)}</div>
  </div>`).join('');
}

async function refreshSummary() {
  STATE.summary = await api('/api/summary?lang=' + LANG);
  const s = STATE.summary;
  $('#stageLabel').textContent = s.trimester[LANG] || s.trimester.en;
  $('#weekBig').textContent = s.stage === 'pregnancy' ? `${tr('week')} ${s.week}` : (s.stage === 'postpartum' ? tr('stage_postpartum_s') : tr('stage_baby_s'));
  $('#trimesterLabel').textContent = s.stage === 'pregnancy' ? `${s.week} / 40` : '';
  $('#eddDisplay').textContent = s.edd || tr('not_set');
  $('#nextDisplay').textContent = s.next ? (s.next.title[LANG] || s.next.title.en) + ' · ' + s.next.due : tr('all_done');
  const pct = s.stage === 'pregnancy' ? Math.min(100, Math.round(s.week / 40 * 100)) : 100;
  $('#ringPct').textContent = pct + '%';
  $('#progressRing').style.background = `conic-gradient(#ffd98a ${pct}%, transparent 0)`;
  const open = STATE.tasks.filter(t => !t.done).slice(0, 3);
  $('#homeTasks').innerHTML = open.length ? open.map(t => `<div class="task">
    <div class="task__main"><div class="task__title">${esc(t.title[LANG] || t.title.en)}</div>
    <div class="task__meta"><span>${esc(t.due)}</span></div></div></div>`).join('') : `<p class="empty">${esc(tr('all_done'))}</p>`;
}

async function refresh() {
  const state = await api('/api/state');
  STATE.profile = state.profile;
  STATE.tasks = await api('/api/tasks');
  const edu = await api('/api/education?lang=' + LANG);
  renderEducation(edu.items, $('#eduList'));
  renderEducation(edu.items.slice(0, 2), $('#homeEdu'));
  $('#learnStageLine').textContent = edu.stage === 'pregnancy' ? `${tr('week')} ${edu.week}` : tr(edu.stage === 'postpartum' ? 'stage_postpartum_s' : 'stage_baby_s');
  renderTasks();
  await loadTraditions();
  await refreshSummary();
}

(async function init() {
  try { DICT = await api('/api/strings?lang=' + LANG); } catch (_) { DICT = {}; }
  applyLang();
  const state = await api('/api/state');
  if (state.profile) {
    STATE.profile = state.profile;
    LANG = state.profile.language || LANG;
    localStorage.setItem('mc_lang', LANG);
    DICT = await api('/api/strings?lang=' + LANG);
    applyLang();
    await refresh();
    go('home');
  } else {
    $('#pregnancyFields').style.display = 'block';
    go('onboarding');
  }
})();
