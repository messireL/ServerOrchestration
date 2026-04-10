const endpoints = {
  version: '/version',
  summary: '/api/summary',
  servers: '/api/servers',
  groups: '/api/groups',
  statuses: '/api/status/servers',
  alerts: '/api/alerts',
  pingRun: '/api/probes/ping/run',
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
  const tzEl = document.getElementById('timezoneValue');
  if (tzEl) tzEl.textContent = versionInfo.timezone || '—';
  const urlEl = document.getElementById('publicUrlValue');
  if (urlEl) urlEl.textContent = versionInfo.public_base_url || '—';
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
}

function renderGroupOptions(groups, selectedId = '') {
  const select = document.getElementById('attachGroupSelect');
  const options = groups.map(group => `<option value="${group.id}" ${String(group.id) === String(selectedId) ? 'selected' : ''}>${safe(group.name)} (#${group.id})</option>`).join('');
  select.innerHTML = options || '<option value="">Сначала создайте группу</option>';
}

function renderServerOptions(servers, selectedId = '') {
  const select = document.getElementById('attachServerSelect');
  const options = servers.map(server => `<option value="${server.id}" ${String(server.id) === String(selectedId) ? 'selected' : ''}>${safe(server.name)} (${safe(server.host)})</option>`).join('');
  select.innerHTML = options || '<option value="">Сначала добавьте сервер</option>';
}

function renderGroupsList(groups) {
  const container = document.getElementById('groupsList');
  if (!groups.length) {
    container.innerHTML = '<div class="mini-item"><div class="desc">Групп пока нет. Можно начать с тестовой группы и не мучить себя лишней драмой.</div></div>';
    return;
  }

  container.innerHTML = groups.map(group => `
    <div class="mini-item">
      <div class="mini-item-head">
        <strong>${safe(group.name)}</strong>
        <span class="pill pill-info">${safe(group.server_count)} server(s)</span>
      </div>
      <div class="desc">${safe(group.description)}</div>
    </div>
  `).join('');
}

function renderStatuses(items) {
  const body = document.getElementById('statusRows');
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="10" class="empty-cell">Серверы ещё не добавлены. После этого места для скуки станет заметно меньше.</td></tr>';
    return;
  }

  body.innerHTML = items.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td class="server-cell">
        <strong>${safe(item.name)}</strong>
        <span class="muted">${item.is_enabled ? 'Включён' : 'Отключён'}</span>
      </td>
      <td class="code-text">${safe(item.host)}</td>
      <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
      <td>${(item.groups || []).length ? (item.groups || []).map(group => `<span class="pill pill-neutral">${safe(group)}</span>`).join(' ') : '<span class="muted">—</span>'}</td>
      <td>${statusPill(item.ping_ok)}</td>
      <td>${safe(item.ping_latency_ms)}</td>
      <td>${Number(item.active_alerts || 0) > 0 ? `<span class="pill pill-danger">${safe(item.active_alerts)}</span>` : '<span class="pill pill-success">0</span>'}</td>
      <td>${safe(item.last_check_at)}</td>
      <td class="error-text">${safe(item.last_error)}</td>
    </tr>
  `).join('');
}

function renderAlerts(items) {
  const body = document.getElementById('alertRows');
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">Активных alerts пока нет. Пусть так будет подольше.</td></tr>';
    return;
  }

  body.innerHTML = items.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td>
        <strong>${safe(item.server_name)}</strong><br />
        <span class="muted code-text">${safe(item.server_host)}</span>
      </td>
      <td>${safe(item.alert_type)}</td>
      <td>${item.severity === 'critical' ? '<span class="pill pill-danger">critical</span>' : '<span class="pill pill-warning">warning</span>'}</td>
      <td>${safe(item.message)}</td>
      <td>${safe(item.first_seen_at)}</td>
      <td>${safe(item.last_seen_at)}</td>
    </tr>
  `).join('');
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
}

async function runPingProbe() {
  const buttons = [document.getElementById('pingBtn'), document.getElementById('pingBtnSide')];
  buttons.forEach(button => button.disabled = true);
  try {
    const result = await fetchJson(endpoints.pingRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timeout_seconds: 2 }),
    });
    showMessage('success', `Ping probe завершён: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}`);
    await loadDashboard();
  } catch (error) {
    showMessage('error', `Не удалось запустить ping probe: ${error.message}`);
  } finally {
    buttons.forEach(button => button.disabled = false);
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
  } catch (error) {
    showMessage('error', `Не удалось добавить сервер: ${error.message}`);
  }
}

async function handleAttachSubmit(event) {
  event.preventDefault();
  const groupId = document.getElementById('attachGroupSelect').value;
  const serverId = document.getElementById('attachServerSelect').value;
  if (!groupId || !serverId) {
    showMessage('error', 'Для привязки нужны и сервер, и группа. Без них магия не работает.');
    return;
  }

  try {
    await fetchJson(`/api/groups/${groupId}/servers/${serverId}`, { method: 'POST' });
    showMessage('success', 'Сервер успешно привязан к группе.');
    await loadDashboard();
  } catch (error) {
    showMessage('error', `Не удалось привязать сервер к группе: ${error.message}`);
  }
}

function wireEvents() {
  document.getElementById('refreshBtn').addEventListener('click', () => loadDashboard().catch(err => showMessage('error', err.message)));
  document.getElementById('refreshBtnSide').addEventListener('click', () => loadDashboard().catch(err => showMessage('error', err.message)));
  document.getElementById('pingBtn').addEventListener('click', runPingProbe);
  document.getElementById('pingBtnSide').addEventListener('click', runPingProbe);
  document.getElementById('groupForm').addEventListener('submit', handleGroupSubmit);
  document.getElementById('serverForm').addEventListener('submit', handleServerSubmit);
  document.getElementById('attachForm').addEventListener('submit', handleAttachSubmit);
}

wireEvents();
loadDashboard().catch(error => showMessage('error', `Не удалось загрузить dashboard: ${error.message}`));
