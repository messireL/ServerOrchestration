const state = {
  version: null,
  summary: null,
  servers: [],
  groups: [],
  statuses: [],
  alerts: [],
  groupLinks: [],
  serverSearch: '',
  groupSearch: '',
};

const tabMeta = {
  dashboard: { title: 'Главная', lead: 'Короткая сводка по системе, быстрые действия и проблемные места.' },
  servers: { title: 'Серверы', lead: 'Inventory серверов, редактирование карточек и базовые параметры доступа.' },
  groups: { title: 'Группы', lead: 'Группы и связи сервер ↔ группа для дальнейших проверок и действий.' },
  checks: { title: 'Проверки', lead: 'Запуск и просмотр результатов проверок доступности и статусов.' },
  alerts: { title: 'Оповещения', lead: 'Активные уведомления без смешивания с inventory и общей сводкой.' },
  roadmap: { title: 'Дальше', lead: 'Ближайшие шаги развития проекта и operational-контур.' },
};

const endpoints = {
  version: '/version',
  summary: '/api/summary',
  servers: '/api/servers',
  groups: '/api/groups',
  groupLinks: '/api/group-links',
  statuses: '/api/status/servers',
  alerts: '/api/alerts',
  pingRun: '/api/probes/ping/run',
};

const $ = (id) => document.getElementById(id);
const q = (sel) => document.querySelector(sel);
const qa = (sel) => Array.from(document.querySelectorAll(sel));

function safe(value) {
  if (value === null || value === undefined) return '—';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value ?? '—';
}

function showMessage(type, text) {
  const stack = $('messageStack');
  if (!stack) return;
  const div = document.createElement('div');
  div.className = `flash flash-${type}`;
  div.textContent = text;
  stack.prepend(div);
  setTimeout(() => div.remove(), 5000);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload?.detail ? payload.detail : payload;
    throw new Error(String(detail || `HTTP ${response.status}`));
  }
  return payload;
}

function formatTs(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return safe(value);
  return date.toLocaleString('ru-RU');
}

function statusHtml(flag) {
  if (flag === true) return '<span class="status-dot ok">OK</span>';
  if (flag === false) return '<span class="status-dot fail">FAIL</span>';
  return '<span class="status-dot unknown">unknown</span>';
}


function applyTheme(theme) {
  const normalized = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = normalized;
  try { localStorage.setItem('sm-theme', normalized); } catch (e) {}
  const button = $('themeToggleBtn');
  if (button) {
    button.textContent = normalized === 'dark' ? 'Светлая тема' : 'Тёмная тема';
    button.dataset.theme = normalized;
  }
}

function initThemeToggle() {
  const button = $('themeToggleBtn');
  const current = document.documentElement.dataset.theme || 'light';
  applyTheme(current);
  if (!button) return;
  button.addEventListener('click', () => {
    const next = (document.documentElement.dataset.theme || 'light') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
  });
}

function renderMeta(meta) {
  if (!meta) return;
  setText('versionValue', meta.version || '—');
  setText('timezoneValue', meta.timezone || '—');
  setText('publicUrlValue', meta.public_base_url || '—');
  setText('brandName', meta.display_name || 'Система мониторинга');
  setText('pageEyebrow', meta.display_name || 'Система мониторинга');
  if (meta.display_name) document.title = meta.display_name;
}

function renderSummary(summary) {
  const cards = $('summaryCards');
  const quick = $('quickStats');
  if (!cards || !quick || !summary) return;

  const items = [
    ['Всего серверов', summary.servers_total, 'inventory'],
    ['Включено', summary.servers_enabled, 'enabled'],
    ['Групп', summary.groups_total, 'groups'],
    ['Связей', summary.group_links_total, 'links'],
    ['Ping OK', summary.ping_ok_total, 'healthy'],
    ['Ping FAIL', summary.ping_fail_total, 'issues'],
    ['Ping unknown', summary.ping_unknown_total, 'unchecked'],
    ['Активные alerts', summary.active_alerts_total, 'attention'],
  ];

  cards.innerHTML = items.map(([label, value, sub]) => `
    <article class="stat-card">
      <div class="stat-label">${safe(label)}</div>
      <div class="stat-value">${safe(value)}</div>
      <div class="stat-sub">${safe(sub)}</div>
    </article>
  `).join('');

  quick.innerHTML = [
    ['Включено серверов', summary.servers_enabled],
    ['Проблемы по ping', summary.ping_fail_total],
    ['Активные alerts', summary.active_alerts_total],
    ['Группы', summary.groups_total],
  ].map(([label, value]) => `
    <div class="micro-stat">
      <div class="label">${safe(label)}</div>
      <strong>${safe(value)}</strong>
    </div>
  `).join('');
}

function serverMatches(server, query) {
  if (!query) return true;
  const text = [server.name, server.host, server.ssh_user, server.description, ...(server.groups || [])]
    .filter(Boolean).join(' ').toLowerCase();
  return text.includes(query);
}

function groupMatches(group, query) {
  if (!query) return true;
  const text = [group.name, group.description].filter(Boolean).join(' ').toLowerCase();
  return text.includes(query);
}

function renderDashboardServers(items) {
  const body = $('dashboardServerRows');
  if (!body) return;
  const rows = (items || []).slice(0, 6);
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty-cell">Серверы ещё не добавлены. После заполнения inventory здесь появится короткая сводка.</td></tr>';
    return;
  }

  body.innerHTML = rows.map((item) => `
    <tr>
      <td><strong>${safe(item.name)}</strong></td>
      <td class="code-text">${safe(item.host)}</td>
      <td>${statusHtml(item.ping_ok)}</td>
      <td>${safe(item.ping_latency_ms)}</td>
      <td>${Number(item.active_alerts || 0)}</td>
      <td>${formatTs(item.last_check_at)}</td>
    </tr>
  `).join('');
}

function renderAlerts(items) {
  const body = $('alertRows');
  const preview = $('alertsPreview');
  if (body) {
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="7" class="empty-cell">Активных alerts пока нет.</td></tr>';
    } else {
      body.innerHTML = items.map((item) => `
        <tr>
          <td>${safe(item.id)}</td>
          <td><strong>${safe(item.server_name)}</strong><br><span class="code-text">${safe(item.server_host)}</span></td>
          <td>${safe(item.alert_type)}</td>
          <td>${item.severity === 'critical' ? '<span class="pill pill-danger">critical</span>' : '<span class="pill pill-warning">warning</span>'}</td>
          <td>${safe(item.message)}</td>
          <td>${formatTs(item.first_seen_at)}</td>
          <td>${formatTs(item.last_seen_at)}</td>
        </tr>
      `).join('');
    }
  }

  if (preview) {
    if (!items.length) {
      preview.innerHTML = '<div class="alert-mini-item"><div class="alert-mini-text">Активных alerts нет.</div></div>';
    } else {
      preview.innerHTML = items.slice(0, 4).map((item) => `
        <div class="alert-mini-item">
          <div class="alert-mini-head">
            <strong>${safe(item.server_name)}</strong>
            ${item.severity === 'critical' ? '<span class="pill pill-danger">critical</span>' : '<span class="pill pill-warning">warning</span>'}
          </div>
          <div class="alert-mini-text">${safe(item.message)}</div>
        </div>
      `).join('');
    }
  }
}

function renderServersTable(servers, statuses) {
  const body = $('serversListRows');
  if (!body) return;
  const statusMap = new Map((statuses || []).map((s) => [String(s.id), s]));
  const filtered = (servers || []).filter((item) => serverMatches(item, state.serverSearch));
  setText('serversCountLabel', `${filtered.length} серверов`);

  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty-cell">Серверы не найдены. Можно создать первый сервер или сбросить фильтр.</td></tr>';
    return;
  }

  body.innerHTML = filtered.map((item) => {
    const st = statusMap.get(String(item.id)) || {};
    const groups = (item.groups || []).length
      ? `<div class="inline-pills">${item.groups.map((g) => `<span class="pill pill-neutral">${safe(g)}</span>`).join('')}</div>`
      : '<span class="muted">—</span>';
    return `
      <tr>
        <td>
          <strong>${safe(item.name)}</strong><br>
          <span class="code-text">${safe(item.host)}</span>
        </td>
        <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
        <td>${groups}</td>
        <td>${statusHtml(st.ping_ok)}</td>
        <td>${formatTs(st.last_check_at)}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn-secondary" type="button" data-action="edit-server" data-id="${item.id}">Изменить</button>
            <button class="btn btn-danger" type="button" data-action="delete-server" data-id="${item.id}" data-name="${safe(item.name)}">Удалить</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderGroups(groups) {
  const body = $('groupsListRows');
  if (!body) return;
  const filtered = (groups || []).filter((g) => groupMatches(g, state.groupSearch));
  setText('groupsCountLabel', `${filtered.length} групп`);

  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="4" class="empty-cell">Группы не найдены. Создайте новую или сбросьте фильтр.</td></tr>';
    return;
  }

  body.innerHTML = filtered.map((group) => `
    <tr>
      <td><strong>${safe(group.name)}</strong></td>
      <td>${safe(group.description)}</td>
      <td>${safe(group.server_count)}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-secondary" type="button" data-action="edit-group" data-id="${group.id}">Изменить</button>
          <button class="btn btn-danger" type="button" data-action="delete-group" data-id="${group.id}" data-name="${safe(group.name)}">Удалить</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderGroupLinks(links) {
  const body = $('groupLinkRows');
  if (!body) return;
  if (!links.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty-cell">Связей пока нет.</td></tr>';
    return;
  }
  body.innerHTML = links.map((link) => `
    <tr>
      <td><strong>${safe(link.group_name)}</strong></td>
      <td>${safe(link.server_name)}</td>
      <td class="code-text">${safe(link.server_host)}</td>
      <td>${formatTs(link.created_at)}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-danger" type="button" data-action="detach-link" data-group-id="${link.group_id}" data-server-id="${link.server_id}">Убрать</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderStatuses(items) {
  const body = $('statusRows');
  if (!body) return;
  const filtered = (items || []).filter((item) => serverMatches(item, state.serverSearch));
  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="10" class="empty-cell">Серверы не найдены. Добавьте их в inventory.</td></tr>';
    return;
  }
  body.innerHTML = filtered.map((item) => `
    <tr>
      <td>${safe(item.id)}</td>
      <td><strong>${safe(item.name)}</strong></td>
      <td class="code-text">${safe(item.host)}</td>
      <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
      <td>${(item.groups || []).length ? `<div class="inline-pills">${item.groups.map((g) => `<span class="pill pill-neutral">${safe(g)}</span>`).join('')}</div>` : '<span class="muted">—</span>'}</td>
      <td>${statusHtml(item.ping_ok)}</td>
      <td>${safe(item.ping_latency_ms)}</td>
      <td>${Number(item.active_alerts || 0) > 0 ? `<span class="pill pill-danger">${safe(item.active_alerts)}</span>` : '<span class="pill pill-success">0</span>'}</td>
      <td>${formatTs(item.last_check_at)}</td>
      <td>${safe(item.last_error)}</td>
    </tr>
  `).join('');
}

function populateSelect(id, items, emptyText, labelFn) {
  const select = $(id);
  if (!select) return;
  if (!items.length) {
    select.innerHTML = `<option value="">${emptyText}</option>`;
    return;
  }
  select.innerHTML = items.map((item) => `<option value="${item.id}">${labelFn(item)}</option>`).join('');
}

function refreshUi() {
  renderMeta(state.version);
  renderSummary(state.summary);
  renderDashboardServers(state.statuses || []);
  renderAlerts(state.alerts || []);
  renderServersTable(state.servers || [], state.statuses || []);
  renderGroups(state.groups || []);
  renderGroupLinks(state.groupLinks || []);
  renderStatuses(state.statuses || []);
  populateSelect('attachGroupSelect', state.groups || [], 'Сначала создайте группу', (g) => `${g.name} (#${g.id})`);
  populateSelect('attachServerSelect', state.servers || [], 'Сначала добавьте сервер', (s) => `${s.name} (${s.host})`);
}

async function loadAll() {
  const [version, summary, servers, groups, statuses, alerts, groupLinks] = await Promise.all([
    fetchJson(endpoints.version),
    fetchJson(endpoints.summary),
    fetchJson(endpoints.servers),
    fetchJson(endpoints.groups),
    fetchJson(endpoints.statuses),
    fetchJson(endpoints.alerts),
    fetchJson(endpoints.groupLinks),
  ]);
  state.version = version;
  state.summary = summary;
  state.servers = servers;
  state.groups = groups;
  state.statuses = statuses;
  state.alerts = alerts;
  state.groupLinks = groupLinks;
  refreshUi();
}

function setTab(tab) {
  const meta = tabMeta[tab] || tabMeta.dashboard;
  setText('pageTitle', meta.title);
  setText('pageLead', meta.lead);
  qa('.nav-link').forEach((node) => node.classList.toggle('active', node.dataset.tab === tab));
  qa('.view').forEach((node) => node.classList.toggle('active', node.dataset.view === tab));
  window.location.hash = tab;
}

function fillServerForm(server) {
  const form = $('serverForm');
  if (!form) return;
  form.server_id.value = server.id || '';
  form.name.value = server.name || '';
  form.host.value = server.host || '';
  form.ssh_port.value = server.ssh_port || 22;
  form.ssh_user.value = server.ssh_user || 'srvops';
  form.description.value = server.description || '';
  form.is_enabled.checked = !!server.is_enabled;
  form.has_3xui.checked = !!server.has_3xui;
  form.has_ssl_monitoring.checked = !!server.has_ssl_monitoring;
  setText('serverFormTitle', `Редактирование сервера #${server.id}`);
  setText('serverSubmitBtn', 'Сохранить сервер');
  $('serverCancelBtn')?.classList.remove('hidden');
  setTab('servers');
}

function resetServerForm() {
  const form = $('serverForm');
  if (!form) return;
  form.reset();
  form.server_id.value = '';
  form.ssh_port.value = 22;
  form.ssh_user.value = 'srvops';
  form.is_enabled.checked = true;
  setText('serverFormTitle', 'Новый сервер');
  setText('serverSubmitBtn', 'Добавить сервер');
  $('serverCancelBtn')?.classList.add('hidden');
}

function fillGroupForm(group) {
  const form = $('groupForm');
  if (!form) return;
  form.group_id.value = group.id || '';
  form.name.value = group.name || '';
  form.description.value = group.description || '';
  setText('groupFormTitle', `Редактирование группы #${group.id}`);
  setText('groupSubmitBtn', 'Сохранить группу');
  $('groupCancelBtn')?.classList.remove('hidden');
  setTab('groups');
}

function resetGroupForm() {
  const form = $('groupForm');
  if (!form) return;
  form.reset();
  form.group_id.value = '';
  setText('groupFormTitle', 'Новая группа');
  setText('groupSubmitBtn', 'Создать группу');
  $('groupCancelBtn')?.classList.add('hidden');
}

async function handleServerSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const serverId = form.server_id.value;
  const payload = {
    name: form.name.value.trim(),
    host: form.host.value.trim(),
    ssh_port: Number(form.ssh_port.value || 22),
    ssh_user: form.ssh_user.value.trim() || 'srvops',
    description: form.description.value.trim() || null,
    is_enabled: form.is_enabled.checked,
    has_3xui: form.has_3xui.checked,
    has_ssl_monitoring: form.has_ssl_monitoring.checked,
  };
  try {
    const url = serverId ? `${endpoints.servers}/${serverId}` : endpoints.servers;
    const method = serverId ? 'PUT' : 'POST';
    const result = await fetchJson(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    showMessage('success', serverId ? `Сервер «${result.name}» обновлён.` : `Сервер «${result.name}» добавлен.`);
    resetServerForm();
    await loadAll();
    setTab('servers');
  } catch (error) {
    showMessage('error', `Не удалось сохранить сервер: ${error.message}`);
  }
}

async function handleGroupSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const groupId = form.group_id.value;
  const payload = { name: form.name.value.trim(), description: form.description.value.trim() || null };
  try {
    const url = groupId ? `${endpoints.groups}/${groupId}` : endpoints.groups;
    const method = groupId ? 'PUT' : 'POST';
    const result = await fetchJson(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    showMessage('success', groupId ? `Группа «${result.name}» обновлена.` : `Группа «${result.name}» создана.`);
    resetGroupForm();
    await loadAll();
    setTab('groups');
  } catch (error) {
    showMessage('error', `Не удалось сохранить группу: ${error.message}`);
  }
}

async function handleAttachSubmit(event) {
  event.preventDefault();
  const groupId = $('attachGroupSelect')?.value;
  const serverId = $('attachServerSelect')?.value;
  if (!groupId || !serverId) {
    showMessage('error', 'Для привязки выберите группу и сервер.');
    return;
  }
  try {
    await fetchJson(`/api/groups/${groupId}/servers/${serverId}`, { method: 'POST' });
    showMessage('success', 'Связь сервер ↔ группа создана.');
    await loadAll();
  } catch (error) {
    showMessage('error', `Не удалось создать связь: ${error.message}`);
  }
}

async function runPingProbe() {
  const buttons = ['pingBtn', 'pingBtnChecks'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.pingRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timeout_seconds: 2 }),
    });
    showMessage('success', `Ping probe завершён: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить ping probe: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function handleActionClick(event) {
  const btn = event.target.closest('button[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  if (action === 'edit-server') {
    const server = state.servers.find((item) => String(item.id) === String(btn.dataset.id));
    if (server) fillServerForm(server);
    return;
  }
  if (action === 'delete-server') {
    const name = btn.dataset.name || 'сервер';
    if (!window.confirm(`Удалить сервер «${name}»?`)) return;
    try {
      await fetchJson(`${endpoints.servers}/${btn.dataset.id}`, { method: 'DELETE' });
      showMessage('success', `Сервер «${name}» удалён.`);
      resetServerForm();
      await loadAll();
    } catch (error) {
      showMessage('error', `Не удалось удалить сервер: ${error.message}`);
    }
    return;
  }
  if (action === 'edit-group') {
    const group = state.groups.find((item) => String(item.id) === String(btn.dataset.id));
    if (group) fillGroupForm(group);
    return;
  }
  if (action === 'delete-group') {
    const name = btn.dataset.name || 'группа';
    if (!window.confirm(`Удалить группу «${name}»?`)) return;
    try {
      await fetchJson(`${endpoints.groups}/${btn.dataset.id}`, { method: 'DELETE' });
      showMessage('success', `Группа «${name}» удалена.`);
      resetGroupForm();
      await loadAll();
    } catch (error) {
      showMessage('error', `Не удалось удалить группу: ${error.message}`);
    }
    return;
  }
  if (action === 'detach-link') {
    if (!window.confirm('Удалить связь сервер ↔ группа?')) return;
    try {
      await fetchJson(`/api/groups/${btn.dataset.groupId}/servers/${btn.dataset.serverId}`, { method: 'DELETE' });
      showMessage('success', 'Связь сервер ↔ группа удалена.');
      await loadAll();
    } catch (error) {
      showMessage('error', `Не удалось удалить связь: ${error.message}`);
    }
  }
}

function wire() {
  initThemeToggle();
  qa('.nav-link').forEach((node) => node.addEventListener('click', () => setTab(node.dataset.tab)));
  $('refreshBtn')?.addEventListener('click', () => loadAll().catch((e) => showMessage('error', e.message)));
  $('pingBtn')?.addEventListener('click', runPingProbe);
  $('pingBtnChecks')?.addEventListener('click', runPingProbe);
  $('serverForm')?.addEventListener('submit', handleServerSubmit);
  $('groupForm')?.addEventListener('submit', handleGroupSubmit);
  $('attachForm')?.addEventListener('submit', handleAttachSubmit);
  $('serverCancelBtn')?.addEventListener('click', resetServerForm);
  $('groupCancelBtn')?.addEventListener('click', resetGroupForm);
  $('serverSearchInput')?.addEventListener('input', (e) => { state.serverSearch = e.target.value.trim().toLowerCase(); refreshUi(); });
  $('groupSearchInput')?.addEventListener('input', (e) => { state.groupSearch = e.target.value.trim().toLowerCase(); refreshUi(); });
  document.body.addEventListener('click', handleActionClick);
}

async function init() {
  wire();
  const hash = (window.location.hash || '#dashboard').replace('#', '');
  setTab(tabMeta[hash] ? hash : 'dashboard');
  try {
    await loadAll();
  } catch (error) {
    showMessage('error', `Не удалось загрузить данные панели: ${error.message}`);
  }
}

document.addEventListener('DOMContentLoaded', init);
