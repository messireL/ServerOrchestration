const endpoints = {
  version: '/version',
  summary: '/api/summary',
  statuses: '/api/status/servers',
  alerts: '/api/alerts',
  groups: '/api/groups',
  servers: '/api/servers',
  pingRun: '/api/probes/ping/run',
};

const tabMeta = {
  dashboard: {
    title: 'Главная',
    lead: 'Сводка по инфраструктуре, status-карточки и быстрые действия.',
  },
  servers: {
    title: 'Серверы',
    lead: 'Добавление и просмотр серверов, чтобы inventory жил не в терминале и молитвах.',
  },
  groups: {
    title: 'Группы',
    lead: 'Группировка серверов под будущие сценарии и maintenance windows.',
  },
  checks: {
    title: 'Проверки',
    lead: 'Запуск доступных probe и единая таблица текущих status-данных.',
  },
  alerts: {
    title: 'Оповещения',
    lead: 'Активные alerts отдельно, чтобы проблемы не тонули в формах и summary.',
  },
  roadmap: {
    title: 'Дальше',
    lead: 'Куда растёт проект после UI-перестройки и почему это уже нормальная панель, а не простыня.',
  },
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
  document.getElementById('version').textContent = versionInfo.version || '—';
  document.getElementById('timezoneValue').textContent = versionInfo.timezone || '—';
  document.getElementById('publicUrlValue').textContent = versionInfo.public_base_url || '—';
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
    <div class="info-chip">
      <div class="label">Включено серверов</div>
      <strong>${safe(summary.servers_enabled)}</strong>
    </div>
    <div class="info-chip">
      <div class="label">Проблемы по ping</div>
      <strong>${safe(summary.ping_fail_total)}</strong>
    </div>
    <div class="info-chip">
      <div class="label">Активные alerts</div>
      <strong>${safe(summary.active_alerts_total)}</strong>
    </div>
    <div class="info-chip">
      <div class="label">Группы</div>
      <strong>${safe(summary.groups_total)}</strong>
    </div>
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

function renderGroupsList(groups) {
  const container = document.getElementById('groupsList');
  if (!container) return;
  if (!groups.length) {
    container.innerHTML = '<div class="group-item"><div class="muted">Групп пока нет. Начни с test или prod — без философии, просто чтобы было на что опираться.</div></div>';
    return;
  }

  container.innerHTML = groups.map(group => `
    <div class="group-item">
      <div class="group-item-head">
        <strong>${safe(group.name)}</strong>
        <span class="pill pill-info">${safe(group.server_count)} server(s)</span>
      </div>
      <div class="muted">${safe(group.description)}</div>
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
    </article>
  `;
}

function renderServerCards(targetId, items, emptyText) {
  const container = document.getElementById(targetId);
  if (!container) return;
  if (!items.length) {
    container.innerHTML = `<article class="server-card"><div class="muted">${safe(emptyText)}</div></article>`;
    return;
  }
  container.innerHTML = items.map(renderServerCard).join('');
}

function renderStatuses(items) {
  const body = document.getElementById('statusRows');
  if (!body) return;
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="10" class="empty-cell">Серверы ещё не добавлены. После этого панель станет куда полезнее и менее теоретической.</td></tr>';
    return;
  }

  body.innerHTML = items.map(item => `
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
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">Активных alerts пока нет. И вот тут хочется просто тихо порадоваться.</td></tr>';
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

async function loadDashboard() {
  const [version, summary, statuses, alerts, groups, servers] = await Promise.all([
    fetchJson(endpoints.version),
    fetchJson(endpoints.summary),
    fetchJson(endpoints.statuses),
    fetchJson(endpoints.alerts),
    fetchJson(endpoints.groups),
    fetchJson(endpoints.servers),
  ]);

  renderMeta(version);
  renderSummary(summary);
  renderStatuses(statuses);
  renderAlerts(alerts);
  renderGroupsList(groups);
  renderGroupOptions(groups);
  renderServerOptions(servers);
  renderServerCards('dashboardServerCards', statuses.slice(0, 6), 'Серверы ещё не добавлены. Пока это красивая, но слишком спокойная панель.');
  renderServerCards('serversListCards', statuses, 'Список серверов пока пуст. Добавим их на этой же вкладке и пойдём дальше.');
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
  const payload = {
    name: form.name.value.trim(),
    description: form.description.value.trim() || null,
  };

  try {
    const result = await fetchJson(endpoints.groups, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    showMessage('success', `Группа «${result.name}» создана.`);
    form.reset();
    await loadDashboard();
    renderGroupOptions(await fetchJson(endpoints.groups), result.id);
    setActiveTab('groups');
  } catch (error) {
    showMessage('error', `Не удалось создать группу: ${error.message}`);
  }
}

async function handleServerSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
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
    const result = await fetchJson(endpoints.servers, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    showMessage('success', `Сервер «${result.name}» добавлен.`);
    form.reset();
    form.ssh_port.value = '22';
    form.ssh_user.value = 'srvops';
    form.is_enabled.checked = true;
    await loadDashboard();
    renderServerOptions(await fetchJson(endpoints.servers), result.id);
    setActiveTab('servers');
  } catch (error) {
    showMessage('error', `Не удалось добавить сервер: ${error.message}`);
  }
}

async function handleAttachSubmit(event) {
  event.preventDefault();
  const groupId = document.getElementById('attachGroupSelect').value;
  const serverId = document.getElementById('attachServerSelect').value;
  if (!groupId || !serverId) {
    showMessage('error', 'Для привязки нужны и сервер, и группа. Без этого получится только философская привязка к пустоте.');
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

function wireEvents() {
  document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', () => setActiveTab(button.dataset.tab));
  });

  ['refreshBtn', 'refreshBtnMain'].forEach(id => {
    const element = document.getElementById(id);
    if (element) element.addEventListener('click', () => loadDashboard().catch(err => showMessage('error', err.message)));
  });

  ['pingBtn', 'pingBtnMain', 'pingBtnChecks'].forEach(id => {
    const element = document.getElementById(id);
    if (element) element.addEventListener('click', runPingProbe);
  });

  document.getElementById('groupForm').addEventListener('submit', handleGroupSubmit);
  document.getElementById('serverForm').addEventListener('submit', handleServerSubmit);
  document.getElementById('attachForm').addEventListener('submit', handleAttachSubmit);

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    setActiveTab(hash in tabMeta ? hash : 'dashboard');
  });
}

wireEvents();
setActiveTab((window.location.hash || '#dashboard').replace('#', ''));
loadDashboard().catch(error => showMessage('error', `Не удалось загрузить dashboard: ${error.message}`));
