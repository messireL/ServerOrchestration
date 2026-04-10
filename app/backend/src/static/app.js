const endpoints = {
  version: '/version',
  summary: '/api/summary',
  statuses: '/api/status/servers',
  alerts: '/api/alerts',
  groups: '/api/groups',
  groupLinks: '/api/group-links',
  servers: '/api/servers',
  pingRun: '/api/probes/ping/run',
};

const tabMeta = {
  dashboard: { title: 'Главная', lead: 'Сводка по инфраструктуре, status-карточки и быстрые действия.' },
  servers: { title: 'Серверы', lead: 'Добавление, редактирование и сопровождение inventory серверов.' },
  groups: { title: 'Группы', lead: 'Группировка серверов под будущие сценарии, maintenance windows и Ansible-действия.' },
  checks: { title: 'Проверки', lead: 'Запуск доступных probe и единая таблица текущих status-данных.' },
  alerts: { title: 'Оповещения', lead: 'Активные alerts отдельно, чтобы проблемы не тонули в общем списке.' },
  roadmap: { title: 'Дальше', lead: 'Roadmap ближайших доработок и основные архитектурные ориентиры проекта.' },
};

const state = {
  version: null,
  summary: null,
  statuses: [],
  alerts: [],
  groups: [],
  servers: [],
  groupLinks: [],
  serverSearch: '',
  groupSearch: '',
};

function safe(value) {
  if (value === null || value === undefined || value === '') return '—';
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function statusPill(value) {
  if (value === true) return '<span class="pill pill-success">OK</span>';
  if (value === false) return '<span class="pill pill-danger">FAIL</span>';
  return '<span class="pill pill-warning">N/A</span>';
}

function formatTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return safe(value);
  return safe(date.toLocaleString('ru-RU'));
}

function byId(id) {
  return document.getElementById(id);
}

function showMessage(type, text) {
  const stack = document.getElementById('messageStack');
  const item = document.createElement('div');
  item.className = `message ${type} show`;
  item.textContent = text;
  stack.prepend(item);
  window.setTimeout(() => {
    item.classList.remove('show');
    item.remove();
  }, 5000);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || `HTTP ${response.status}`);
  }
  return data;
}

function renderMeta(versionInfo) {
  const versionEl = document.getElementById('version');
  const timezoneEl = document.getElementById('timezoneValue');
  const publicUrlEl = document.getElementById('publicUrlValue');

  if (versionEl) versionEl.textContent = versionInfo.version || '—';
  if (timezoneEl) timezoneEl.textContent = versionInfo.timezone || '—';
  if (publicUrlEl) publicUrlEl.textContent = versionInfo.public_base_url || '—';

  if (versionInfo.display_name) {
    document.title = versionInfo.display_name;
    document.querySelectorAll('.brand-title').forEach((el) => { el.textContent = versionInfo.display_name; });
  }
}

function renderSummary(summary) {
  const cards = [
    ['Всего серверов', summary.servers_total, 'inventory'],
    ['Включено', summary.servers_enabled, 'enabled'],
    ['Групп', summary.groups_total, 'groups'],
    ['Связей сервер-группа', summary.group_links_total, 'links'],
    ['Ping OK', summary.ping_ok_total, 'healthy'],
    ['Ping FAIL', summary.ping_fail_total, 'issues'],
    ['Ping unknown', summary.ping_unknown_total, 'unchecked'],
    ['Активные alerts', summary.active_alerts_total, 'attention'],
  ];

  document.getElementById('summaryCards').innerHTML = cards.map(([label, value, sub]) => `
    <article class="summary-card">
      <div class="label">${safe(label)}</div>
      <div class="value">${safe(value)}</div>
      <div class="subvalue">${safe(sub)}</div>
    </article>
  `).join('');

  document.getElementById('quickStats').innerHTML = `
    <div class="info-chip"><div class="label">Включено серверов</div><strong>${safe(summary.servers_enabled)}</strong></div>
    <div class="info-chip"><div class="label">Проблемы по ping</div><strong>${safe(summary.ping_fail_total)}</strong></div>
    <div class="info-chip"><div class="label">Активные alerts</div><strong>${safe(summary.active_alerts_total)}</strong></div>
    <div class="info-chip"><div class="label">Группы</div><strong>${safe(summary.groups_total)}</strong></div>
  `;
}

function renderGroupOptions(groups, selectedId = '') {
  const select = document.getElementById('attachGroupSelect');
  if (!select) return;
  const options = groups.map(group => `<option value="${group.id}" ${String(group.id) === String(selectedId) ? 'selected' : ''}>${safe(group.name)} (#${group.id})</option>`).join('');
  select.innerHTML = options || '<option value="">Сначала создайте группу</option>';
}

function renderServerOptions(servers, selectedId = '') {
  const select = document.getElementById('attachServerSelect');
  if (!select) return;
  const options = servers.map(server => `<option value="${server.id}" ${String(server.id) === String(selectedId) ? 'selected' : ''}>${safe(server.name)} (${safe(server.host)})</option>`).join('');
  select.innerHTML = options || '<option value="">Сначала добавьте сервер</option>';
}

function serverMatchesSearch(item, query) {
  if (!query) return true;
  const haystack = [item.name, item.host, item.ssh_user, item.description, ...(item.groups || [])]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(query);
}

function groupMatchesSearch(item, query) {
  if (!query) return true;
  const haystack = [item.name, item.description].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(query);
}

function renderGroupsList(groups) {
  const container = document.getElementById('groupsList');
  if (!container) return;
  const filtered = groups.filter(group => groupMatchesSearch(group, state.groupSearch));
  document.getElementById('groupsCountLabel').textContent = `${filtered.length} групп`;

  if (!filtered.length) {
    container.innerHTML = '<div class="group-item"><div class="muted">Группы не найдены. Можно создать новую или сбросить фильтр.</div></div>';
    return;
  }

  container.innerHTML = filtered.map(group => `
    <div class="group-item">
      <div class="group-item-head">
        <div>
          <strong>${safe(group.name)}</strong>
          <div class="muted">${safe(group.description)}</div>
        </div>
        <div class="group-actions-wrap">
          <span class="pill pill-info">${safe(group.server_count)} server(s)</span>
          <div class="inline-actions">
            <button class="secondary small-btn" type="button" data-action="edit-group" data-id="${group.id}">Изменить</button>
            <button class="secondary small-btn danger-ghost" type="button" data-action="delete-group" data-id="${group.id}" data-name="${safe(group.name)}">Удалить</button>
          </div>
        </div>
      </div>
    </div>
  `).join('');
}

function renderServerCard(item) {
  const groupsHtml = (item.groups || []).length
    ? item.groups.map(group => `<span class="pill pill-neutral">${safe(group)}</span>`).join(' ')
    : '<span class="muted">Группы пока не назначены</span>';

  const featureFlags = [
    item.has_3xui ? '<span class="pill pill-info">3x-ui</span>' : '',
    item.has_ssl_monitoring ? '<span class="pill pill-warning">SSL</span>' : '',
    item.is_enabled ? '<span class="pill pill-success">enabled</span>' : '<span class="pill pill-warning">disabled</span>',
  ].filter(Boolean).join(' ');

  return `
    <article class="server-card">
      <div class="server-card-head">
        <div>
          <div class="server-title">${safe(item.name)}</div>
          <div class="server-subtitle code-text">${safe(item.host)} · ${safe(item.ssh_user)}:${safe(item.ssh_port)}</div>
        </div>
        ${statusPill(item.ping_ok)}
      </div>
      <div class="server-groups">${groupsHtml}</div>
      <div class="server-flags" style="margin-top:10px;">${featureFlags}</div>
      <div class="server-footer">
        <div>Latency: <strong>${safe(item.ping_latency_ms)}</strong></div>
        <div>Alerts: <strong>${safe(item.active_alerts || 0)}</strong></div>
        <div>Проверка: <strong>${formatTimestamp(item.last_check_at)}</strong></div>
        <div class="error-text">${safe(item.last_error)}</div>
      </div>
      <div class="card-actions">
        <button class="secondary small-btn" type="button" data-action="edit-server" data-id="${item.id}">Изменить</button>
        <button class="secondary small-btn danger-ghost" type="button" data-action="delete-server" data-id="${item.id}" data-name="${safe(item.name)}">Удалить</button>
      </div>
    </article>
  `;
}

function renderServerCards(targetId, items, emptyText) {
  const container = document.getElementById(targetId);
  if (!container) return;
  const filtered = targetId === 'serversListCards'
    ? items.filter(item => serverMatchesSearch(item, state.serverSearch))
    : items;
  if (targetId === 'serversListCards') {
    document.getElementById('serversCountLabel').textContent = `${filtered.length} серверов`;
  }
  if (!filtered.length) {
    container.innerHTML = `<article class="server-card"><div class="muted">${safe(emptyText)}</div></article>`;
    return;
  }
  container.innerHTML = filtered.map(renderServerCard).join('');
}

function renderStatuses(items) {
  const body = document.getElementById('statusRows');
  if (!body) return;
  const filtered = items.filter(item => serverMatchesSearch(item, state.serverSearch));
  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="10" class="empty-cell">Серверы не найдены. Добавьте их или измените фильтр.</td></tr>';
    return;
  }

  body.innerHTML = filtered.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td><strong>${safe(item.name)}</strong><br /><span class="muted">${item.is_enabled ? 'Включён' : 'Отключён'}</span></td>
      <td class="code-text">${safe(item.host)}</td>
      <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
      <td>${(item.groups || []).length ? item.groups.map(group => `<span class="pill pill-neutral">${safe(group)}</span>`).join(' ') : '<span class="muted">—</span>'}</td>
      <td>${statusPill(item.ping_ok)}</td>
      <td>${safe(item.ping_latency_ms)}</td>
      <td>${Number(item.active_alerts || 0) > 0 ? `<span class="pill pill-danger">${safe(item.active_alerts)}</span>` : '<span class="pill pill-success">0</span>'}</td>
      <td>${formatTimestamp(item.last_check_at)}</td>
      <td class="error-text">${safe(item.last_error)}</td>
    </tr>
  `).join('');
}

function renderAlerts(items) {
  const body = document.getElementById('alertRows');
  const preview = document.getElementById('alertsPreview');
  if (!body || !preview) return;

  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">Активных alerts пока нет.</td></tr>';
    preview.innerHTML = '<div class="mini-alert-item"><div class="muted">Активных alerts нет.</div></div>';
    return;
  }

  body.innerHTML = items.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td><strong>${safe(item.server_name)}</strong><br /><span class="muted code-text">${safe(item.server_host)}</span></td>
      <td>${safe(item.alert_type)}</td>
      <td>${item.severity === 'critical' ? '<span class="pill pill-danger">critical</span>' : '<span class="pill pill-warning">warning</span>'}</td>
      <td>${safe(item.message)}</td>
      <td>${formatTimestamp(item.first_seen_at)}</td>
      <td>${formatTimestamp(item.last_seen_at)}</td>
    </tr>
  `).join('');

  preview.innerHTML = items.slice(0, 4).map(item => `
    <div class="mini-alert-item">
      <div class="mini-alert-head">
        <strong>${safe(item.server_name)}</strong>
        ${item.severity === 'critical' ? '<span class="pill pill-danger">critical</span>' : '<span class="pill pill-warning">warning</span>'}
      </div>
      <div class="muted">${safe(item.message)}</div>
      <div class="muted" style="margin-top:6px;">${formatTimestamp(item.last_seen_at)}</div>
    </div>
  `).join('');
}

function renderGroupLinks(links) {
  const body = document.getElementById('groupLinkRows');
  if (!body) return;
  if (!links.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty-cell">Связей пока нет. После привязки серверов к группам таблица заполнится.</td></tr>';
    return;
  }

  body.innerHTML = links.map(link => `
    <tr>
      <td><strong>${safe(link.group_name)}</strong></td>
      <td>${safe(link.server_name)}</td>
      <td class="code-text">${safe(link.server_host)}</td>
      <td>${formatTimestamp(link.created_at)}</td>
      <td><button class="secondary small-btn danger-ghost" type="button" data-action="detach-link" data-group-id="${link.group_id}" data-server-id="${link.server_id}">Убрать</button></td>
    </tr>
  `).join('');
}

function fillServerForm(server) {
  const form = document.getElementById('serverForm');
  form.server_id.value = server.id;
  form.name.value = server.name || '';
  form.host.value = server.host || '';
  form.ssh_port.value = server.ssh_port || 22;
  form.ssh_user.value = server.ssh_user || 'srvops';
  form.description.value = server.description || '';
  form.is_enabled.checked = Boolean(server.is_enabled);
  form.has_3xui.checked = Boolean(server.has_3xui);
  form.has_ssl_monitoring.checked = Boolean(server.has_ssl_monitoring);

  document.getElementById('serverFormTitle').textContent = `Редактирование сервера #${server.id}`;
  document.getElementById('serverSubmitBtn').textContent = 'Сохранить сервер';
  document.getElementById('serverCancelBtn').classList.remove('hidden');
  setActiveTab('servers');
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetServerForm() {
  const form = document.getElementById('serverForm');
  form.reset();
  form.server_id.value = '';
  form.ssh_port.value = '22';
  form.ssh_user.value = 'srvops';
  form.is_enabled.checked = true;
  document.getElementById('serverFormTitle').textContent = 'Новый сервер';
  document.getElementById('serverSubmitBtn').textContent = 'Добавить сервер';
  document.getElementById('serverCancelBtn').classList.add('hidden');
}

function fillGroupForm(group) {
  const form = document.getElementById('groupForm');
  form.group_id.value = group.id;
  form.name.value = group.name || '';
  form.description.value = group.description || '';
  document.getElementById('groupFormTitle').textContent = `Редактирование группы #${group.id}`;
  document.getElementById('groupSubmitBtn').textContent = 'Сохранить группу';
  document.getElementById('groupCancelBtn').classList.remove('hidden');
  setActiveTab('groups');
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetGroupForm() {
  const form = document.getElementById('groupForm');
  form.reset();
  form.group_id.value = '';
  document.getElementById('groupFormTitle').textContent = 'Новая группа';
  document.getElementById('groupSubmitBtn').textContent = 'Создать группу';
  document.getElementById('groupCancelBtn').classList.add('hidden');
}

function setActiveTab(tab) {
  const meta = tabMeta[tab] || tabMeta.dashboard;
  document.getElementById('pageTitle').textContent = meta.title;
  document.getElementById('pageLead').textContent = meta.lead;

  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.toggle('active', view.dataset.view === tab);
  });
  window.location.hash = tab;
}

function refreshUi() {
  renderMeta(state.version || {});
  renderSummary(state.summary || {
    servers_total: 0, servers_enabled: 0, groups_total: 0, group_links_total: 0,
    ping_ok_total: 0, ping_fail_total: 0, ping_unknown_total: 0, active_alerts_total: 0,
  });
  renderStatuses(state.statuses || []);
  renderAlerts(state.alerts || []);
  renderGroupsList(state.groups || []);
  renderGroupOptions(state.groups || []);
  renderServerOptions(state.servers || []);
  renderGroupLinks(state.groupLinks || []);
  renderServerCards('dashboardServerCards', (state.statuses || []).slice(0, 6), 'Серверы ещё не добавлены. Пока это спокойная, но слишком пустая панель.');
  renderServerCards('serversListCards', state.servers || [], 'Список серверов пока пуст. Здесь же можно сразу создать первый сервер.');
}

async function loadDashboard() {
  const [version, summary, statuses, alerts, groups, servers, groupLinks] = await Promise.all([
    fetchJson(endpoints.version),
    fetchJson(endpoints.summary),
    fetchJson(endpoints.statuses),
    fetchJson(endpoints.alerts),
    fetchJson(endpoints.groups),
    fetchJson(endpoints.servers),
    fetchJson(endpoints.groupLinks),
  ]);

  state.version = version;
  state.summary = summary;
  state.statuses = statuses;
  state.alerts = alerts;
  state.groups = groups;
  state.servers = servers;
  state.groupLinks = groupLinks;
  refreshUi();
}

async function runPingProbe() {
  const buttons = ['pingBtn', 'pingBtnMain', 'pingBtnChecks']
    .map(id => document.getElementById(id))
    .filter(Boolean);
  buttons.forEach(button => { button.disabled = true; });
  try {
    const result = await fetchJson(endpoints.pingRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timeout_seconds: 2 }),
    });
    showMessage('success', `Ping probe завершён: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}`);
    await loadDashboard();
    setActiveTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить ping probe: ${error.message}`);
  } finally {
    buttons.forEach(button => { button.disabled = false; });
  }
}

async function handleGroupSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const groupId = form.group_id.value;
  const payload = {
    name: form.name.value.trim(),
    description: form.description.value.trim() || null,
  };

  try {
    const result = await fetchJson(groupId ? `${endpoints.groups}/${groupId}` : endpoints.groups, {
      method: groupId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    showMessage('success', groupId ? `Группа «${result.name}» обновлена.` : `Группа «${result.name}» создана.`);
    resetGroupForm();
    await loadDashboard();
    setActiveTab('groups');
  } catch (error) {
    showMessage('error', `Не удалось сохранить группу: ${error.message}`);
  }
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
    const result = await fetchJson(serverId ? `${endpoints.servers}/${serverId}` : endpoints.servers, {
      method: serverId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    showMessage('success', serverId ? `Сервер «${result.name}» обновлён.` : `Сервер «${result.name}» добавлен.`);
    resetServerForm();
    await loadDashboard();
    setActiveTab('servers');
  } catch (error) {
    showMessage('error', `Не удалось сохранить сервер: ${error.message}`);
  }
}

async function handleAttachSubmit(event) {
  event.preventDefault();
  const groupId = document.getElementById('attachGroupSelect').value;
  const serverId = document.getElementById('attachServerSelect').value;
  if (!groupId || !serverId) {
    showMessage('error', 'Для привязки выберите и сервер, и группу.');
    return;
  }

  try {
    await fetchJson(`/api/groups/${groupId}/servers/${serverId}`, { method: 'POST' });
    showMessage('success', 'Сервер успешно привязан к группе.');
    await loadDashboard();
    setActiveTab('groups');
  } catch (error) {
    showMessage('error', `Не удалось привязать сервер к группе: ${error.message}`);
  }
}

async function handleCardActions(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const action = button.dataset.action;

  if (action === 'edit-server') {
    const server = state.servers.find(item => String(item.id) === String(button.dataset.id));
    if (server) fillServerForm(server);
    return;
  }

  if (action === 'delete-server') {
    const serverId = button.dataset.id;
    const serverName = button.dataset.name || `#${serverId}`;
    if (!window.confirm(`Удалить сервер «${serverName}»?`)) return;
    try {
      await fetchJson(`${endpoints.servers}/${serverId}`, { method: 'DELETE' });
      showMessage('success', `Сервер «${serverName}» удалён.`);
      resetServerForm();
      await loadDashboard();
    } catch (error) {
      showMessage('error', `Не удалось удалить сервер: ${error.message}`);
    }
    return;
  }

  if (action === 'edit-group') {
    const group = state.groups.find(item => String(item.id) === String(button.dataset.id));
    if (group) fillGroupForm(group);
    return;
  }

  if (action === 'delete-group') {
    const groupId = button.dataset.id;
    const groupName = button.dataset.name || `#${groupId}`;
    if (!window.confirm(`Удалить группу «${groupName}»? Связи с серверами тоже будут удалены.`)) return;
    try {
      await fetchJson(`${endpoints.groups}/${groupId}`, { method: 'DELETE' });
      showMessage('success', `Группа «${groupName}» удалена.`);
      resetGroupForm();
      await loadDashboard();
    } catch (error) {
      showMessage('error', `Не удалось удалить группу: ${error.message}`);
    }
    return;
  }

  if (action === 'detach-link') {
    const groupId = button.dataset.groupId;
    const serverId = button.dataset.serverId;
    if (!window.confirm('Удалить эту связь сервер ↔ группа?')) return;
    try {
      await fetchJson(`/api/groups/${groupId}/servers/${serverId}`, { method: 'DELETE' });
      showMessage('success', 'Связь сервер ↔ группа удалена.');
      await loadDashboard();
    } catch (error) {
      showMessage('error', `Не удалось удалить связь: ${error.message}`);
    }
  }
}

function wireEvents() {
  document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', () => setActiveTab(button.dataset.tab));
  });

  ['refreshBtn', 'refreshBtnMain'].forEach(id => {
    const element = byId(id);
    if (element) element.addEventListener('click', () => loadDashboard().catch(err => showMessage('error', err.message)));
  });

  ['pingBtn', 'pingBtnMain', 'pingBtnChecks'].forEach(id => {
    const element = byId(id);
    if (element) element.addEventListener('click', runPingProbe);
  });

  const groupForm = byId('groupForm');
  if (groupForm) groupForm.addEventListener('submit', handleGroupSubmit);
  const serverForm = byId('serverForm');
  if (serverForm) serverForm.addEventListener('submit', handleServerSubmit);
  const attachForm = byId('attachForm');
  if (attachForm) attachForm.addEventListener('submit', handleAttachSubmit);
  const groupCancelBtn = byId('groupCancelBtn');
  if (groupCancelBtn) groupCancelBtn.addEventListener('click', resetGroupForm);
  const serverCancelBtn = byId('serverCancelBtn');
  if (serverCancelBtn) serverCancelBtn.addEventListener('click', resetServerForm);

  const serverSearchInput = byId('serverSearchInput');
  if (serverSearchInput) {
    serverSearchInput.addEventListener('input', event => {
      state.serverSearch = event.target.value.trim().toLowerCase();
      renderServerCards('serversListCards', state.servers || [], 'Список серверов пока пуст. Здесь же можно сразу создать первый сервер.');
      renderStatuses(state.statuses || []);
    });
  }

  const groupSearchInput = byId('groupSearchInput');
  if (groupSearchInput) {
    groupSearchInput.addEventListener('input', event => {
      state.groupSearch = event.target.value.trim().toLowerCase();
      renderGroupsList(state.groups || []);
    });
  }

  document.body.addEventListener('click', handleCardActions);

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    setActiveTab(hash in tabMeta ? hash : 'dashboard');
  });
}

wireEvents();
setActiveTab((window.location.hash || '#dashboard').replace('#', ''));
loadDashboard().catch(error => showMessage('error', `Не удалось загрузить dashboard: ${error.message}`));
