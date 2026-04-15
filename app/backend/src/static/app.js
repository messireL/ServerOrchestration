const state = {
  version: null,
  summary: null,
  servers: [],
  groups: [],
  statuses: [],
  alerts: [],
  groupLinks: [],
  monitorSettings: null,
  alertSettings: null,
  alertDeliveries: [],
  probeHistory: [],
  serverSearch: '',
  groupSearch: '',
  serverFilter: 'all',
  lastLoadedAt: null,
};

const tabMeta = {
  dashboard: { title: 'Главная', lead: 'Короткая сводка по системе, быстрые действия и проблемные места.' },
  servers: { title: 'Серверы', lead: 'Inventory серверов, редактирование карточек и базовые параметры доступа.' },
  groups: { title: 'Группы', lead: 'Группы и связи сервер ↔ группа для дальнейших проверок и действий.' },
  checks: { title: 'Проверки', lead: 'Фоновый мониторинг, ручные проверки и история прогонов по серверам.' },
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
  alertSettings: '/api/alerts/settings',
  alertDeliveries: '/api/alerts/deliveries?limit=80',
  alertTest: '/api/alerts/test',
  monitorSettings: '/api/monitor/settings',
  probeHistory: '/api/probes/history?limit=80',
  pingRun: '/api/probes/ping/run',
  pingDiagnostics: '/api/probes/ping/diagnostics',
  sshRun: '/api/probes/ssh/run',
  httpRun: '/api/probes/http/run',
  allRun: '/api/probes/connectivity/run',
  xuiRun: '/api/probes/xui/run',
  sslRun: '/api/probes/ssl/run',
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

function formatLatency(value) {
  if (value === null || value === undefined || value === '') return '—';
  return `${safe(value)} ms`;
}

function truncateText(value, max = 96) {
  const text = value == null ? '' : String(value);
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

function statusPillHtml(label, flag, disabledLabel = null) {
  if (disabledLabel && flag === null) {
    return `<span class="status-pill disabled">${safe(label)}: ${safe(disabledLabel)}</span>`;
  }
  const cls = flag === true ? 'ok' : flag === false ? 'fail' : 'unknown';
  const value = flag === true ? 'OK' : flag === false ? 'FAIL' : 'unknown';
  return `<span class="status-pill ${cls}">${safe(label)}: ${value}</span>`;
}

function serverHasIssues(item) {
  return item.ping_ok === false
    || item.ssh_ok === false
    || item.http_ok === false
    || item.console_3xui_ok === false
    || item.subscription_3xui_ok === false
    || Number(item.active_alerts || 0) > 0;
}

function applyServerFilter(items) {
  const list = items || [];
  switch (state.serverFilter) {
    case 'enabled':
      return list.filter((item) => item.is_enabled);
    case 'issues':
      return list.filter((item) => serverHasIssues(item));
    case 'alerts':
      return list.filter((item) => Number(item.active_alerts || 0) > 0);
    case 'http':
      return list.filter((item) => item.has_http_monitoring);
    case 'xui':
      return list.filter((item) => item.has_3xui);
    default:
      return list;
  }
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

function formatApiError(payload, status) {
  if (payload === null || payload === undefined || payload === '') return `HTTP ${status}`;
  if (typeof payload === 'string') return payload;
  if (Array.isArray(payload)) {
    return payload.map((item) => formatApiError(item, status)).filter(Boolean).join('; ');
  }
  if (typeof payload === 'object') {
    if (payload.detail !== undefined) return formatApiError(payload.detail, status);
    const parts = [];
    if (payload.msg) parts.push(String(payload.msg));
    if (Array.isArray(payload.loc) && payload.loc.length) parts.push(`loc=${payload.loc.join('.')}`);
    if (payload.type) parts.push(String(payload.type));
    if (parts.length) return parts.join(' · ');
    try {
      return JSON.stringify(payload);
    } catch (error) {
      return `HTTP ${status}`;
    }
  }
  return String(payload);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(payload, response.status));
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

function probeBadgeHtml(label, flag, options = {}) {
  const { disabled = false, detail = '', hoverOnly = false } = options;
  if (disabled) {
    const text = `${label}: off`;
    return `<span class="status-pill disabled" title="${safe(text)}">${safe(text)}</span>`;
  }
  const cls = flag === true ? 'ok' : flag === false ? 'fail' : 'unknown';
  const value = flag === true ? 'OK' : flag === false ? 'FAIL' : 'unknown';
  const baseText = `${label}: ${value}`;
  const fullText = detail ? `${baseText} · ${detail}` : baseText;
  const visibleText = hoverOnly ? baseText : fullText;
  return `<span class="status-pill ${cls}" title="${safe(fullText)}">${safe(visibleText)}</span>`;
}

function latencyBadgeHtml(label, value) {
  return `<span class="metric-pill">${safe(label)}: ${safe(formatLatency(value))}</span>`;
}

function compactUrlHtml(value, emptyLabel = '—') {
  if (!value) return `<span class="muted small-text">${safe(emptyLabel)}</span>`;
  return `<span class="code-text url-wrap" title="${safe(value)}">${safe(value)}</span>`;
}

function errorCellHtml(value) {
  if (!value) return '<div class="error-snippet error-snippet-soft">Ошибок не зафиксировано</div>';
  return `<div class="error-snippet error-snippet-multiline" title="${safe(value)}">${safe(value)}</div>`;
}

function parseSummary(summary) {
  if (!summary) return null;
  if (typeof summary === 'object') return summary;
  try {
    return JSON.parse(summary);
  } catch (error) {
    return null;
  }
}

function formatBytesCompact(value) {
  const size = Number(value);
  if (!Number.isFinite(size)) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let current = size;
  let idx = 0;
  while (current >= 1024 && idx < units.length - 1) {
    current /= 1024;
    idx += 1;
  }
  return idx === 0 ? `${Math.round(current)} ${units[idx]}` : `${current.toFixed(current >= 100 ? 0 : current >= 10 ? 1 : 2)} ${units[idx]}`;
}

function compactProbeDetail(value, max = 36) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function flattenProbePayload(probe) {
  if (!probe || typeof probe !== 'object') return probe || null;
  const details = probe.details && typeof probe.details === 'object' ? probe.details : null;
  const flat = details ? { ...details } : {};
  Object.entries(probe).forEach(([key, value]) => {
    if (key === 'details') return;
    if (value === undefined || value === null || value === '') return;
    flat[key] = value;
  });
  return flat;
}

function buildContourDetails(item) {
  const summary = parseSummary(item.summary_json);
  if (!summary || typeof summary !== 'object') return {};
  const result = {};
  const http = flattenProbePayload(summary.http || summary.http_last_probe || null);
  const xuiConsole = flattenProbePayload(summary.xui_console || summary.xui_console_last_probe || null);
  const xuiSub = flattenProbePayload(summary.xui_subscription || summary.xui_subscription_last_probe || null);
  const ssl = flattenProbePayload(summary.ssl || summary.ssl_last_probe || null);
  const sslDetails = ssl || null;

  if (http && http.ok && http.status_code) result.http = `HTTP ${http.status_code}`;
  else if (http && (http.error || summary.http_error)) result.http = compactProbeDetail(http.error || summary.http_error, 24);

  if (xuiConsole && xuiConsole.ok && xuiConsole.status_code) result.console = `HTTP ${xuiConsole.status_code}`;
  else if (xuiConsole && (xuiConsole.error || summary.xui_console_error)) result.console = compactProbeDetail(xuiConsole.error || summary.xui_console_error, 24);

  if (xuiSub && xuiSub.ok) {
    const parts = [];
    if (xuiSub.status_code) parts.push(`HTTP ${xuiSub.status_code}`);
    if (Number.isFinite(Number(xuiSub.entries_count)) && Number(xuiSub.entries_count) > 0) parts.push(`${Number(xuiSub.entries_count)} cfg`);
    else if (Number.isFinite(Number(xuiSub.entries)) && Number(xuiSub.entries) > 0) parts.push(`${Number(xuiSub.entries)} cfg`);
    const usedBytes = Number(xuiSub.used_bytes);
    const totalBytes = Number(xuiSub.total_bytes);
    if (Number.isFinite(usedBytes) || Number.isFinite(totalBytes)) {
      const usedLabel = Number.isFinite(usedBytes) ? formatBytesCompact(usedBytes) : '0 B';
      const totalLabel = Number.isFinite(totalBytes) && totalBytes > 0 ? formatBytesCompact(totalBytes) : '∞';
      parts.push(`${usedLabel}/${totalLabel}`);
    }
    if (Number.isFinite(Number(xuiSub.days_remaining))) parts.push(`exp ${Number(xuiSub.days_remaining)}d`);
    else if (xuiSub.expires_at) parts.push(`exp ${String(xuiSub.expires_at).slice(0, 10)}`);
    if (xuiSub.encoding) parts.push(String(xuiSub.encoding));
    if (Array.isArray(xuiSub.entry_types) && xuiSub.entry_types.length) parts.push(xuiSub.entry_types.join(', '));
    if (xuiSub.profile_title) parts.push(String(xuiSub.profile_title));
    result.sub = parts.join(' · ');
  } else if (xuiSub && (xuiSub.payload_error || xuiSub.error || summary.xui_subscription_error)) {
    result.sub = compactProbeDetail(xuiSub.payload_error || xuiSub.error || summary.xui_subscription_error, 28);
  }

  if (ssl && ssl.ok) {
    const parts = [];
    const subjectCn = sslDetails && (sslDetails.subject_cn || (sslDetails.subject && sslDetails.subject.commonName) || (sslDetails.certificate_subject && sslDetails.certificate_subject.commonName) || '');
    const issuerCn = sslDetails && (sslDetails.issuer_cn || (sslDetails.issuer && sslDetails.issuer.commonName) || (sslDetails.certificate_issuer && sslDetails.certificate_issuer.commonName) || '');
    if (subjectCn) parts.push(String(subjectCn));
    else if (issuerCn) parts.push(String(issuerCn));
    if (sslDetails && (sslDetails.self_signed || sslDetails.is_self_signed)) parts.push('self-signed');
    if (sslDetails && Number.isFinite(Number(sslDetails.days_remaining))) parts.push(`${Number(sslDetails.days_remaining)}d`);
    if (sslDetails && sslDetails.hostname_matches === false) parts.push('host mismatch');
    result.ssl = parts.join(' · ') || 'valid';
  } else if (ssl && (ssl.error || summary.ssl_error)) {
    result.ssl = compactProbeDetail(ssl.error || summary.ssl_error, 28);
  }

  return result;
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

function renderSidebarOverview(summary) {
  if (!summary) return;
  setText('sidebarEnabledValue', summary.servers_enabled ?? '—');
  setText('sidebarAlertsValue', summary.active_alerts_total ?? '—');
  setText('sidebarPingValue', summary.ping_ok_total ?? '—');
  setText('sidebarUpdatedValue', state.lastLoadedAt ? formatTs(state.lastLoadedAt) : '—');
}

function renderChecksQuickStats(summary) {
  const quick = $('checksQuickStats');
  if (!quick || !summary) return;
  const schedulerState = summary.scheduler_enabled ? 'on' : 'off';
  const items = [
    ['Ping OK / fail', `${summary.ping_ok_total} / ${summary.ping_fail_total}`],
    ['SSH OK / fail', `${summary.ssh_ok_total} / ${summary.ssh_fail_total}`],
    ['HTTP OK / fail', `${summary.http_ok_total} / ${summary.http_fail_total}`],
    ['Scheduler', schedulerState],
    ['Активные alerts', summary.active_alerts_total],
  ];
  quick.innerHTML = items.map(([label, value]) => `
    <div class="micro-stat">
      <div class="label">${safe(label)}</div>
      <strong>${safe(value)}</strong>
    </div>
  `).join('');
}


function setFormFieldValue(form, fieldName, value) {
  if (!form || !fieldName) return;
  const field = form.elements?.namedItem(fieldName) || form[fieldName];
  if (field && 'value' in field) field.value = value ?? '';
}

function setFormFieldChecked(form, fieldName, checked) {
  if (!form || !fieldName) return;
  const field = form.elements?.namedItem(fieldName) || form[fieldName];
  if (field && 'checked' in field) field.checked = !!checked;
}

function renderMonitorSettings(settings) {
  const form = $('monitorSettingsForm');
  const stats = $('schedulerStats');
  const badge = $('schedulerStateBadge');
  if (badge) {
    badge.textContent = `scheduler: ${settings?.scheduler_enabled ? 'on' : 'off'}`;
    badge.className = settings?.scheduler_enabled ? 'pill pill-success' : 'pill pill-warning';
  }
  if (!form || !settings) return;
  setFormFieldChecked(form, 'scheduler_enabled', settings.scheduler_enabled);
  setFormFieldValue(form, 'ping_interval_seconds', settings.ping_interval_seconds ?? 60);
  setFormFieldValue(form, 'ssh_interval_seconds', settings.ssh_interval_seconds ?? 120);
  setFormFieldValue(form, 'http_interval_seconds', settings.http_interval_seconds ?? 180);
  setFormFieldValue(form, 'ping_timeout_seconds', settings.ping_timeout_seconds ?? 2);
  setFormFieldValue(form, 'tcp_timeout_seconds', settings.tcp_timeout_seconds ?? 3);
  setFormFieldValue(form, 'http_timeout_seconds', settings.http_timeout_seconds ?? 5);
  setFormFieldValue(form, 'xui_interval_seconds', settings.xui_interval_seconds ?? 240);
  setFormFieldValue(form, 'xui_timeout_seconds', settings.xui_timeout_seconds ?? 5);
  setFormFieldValue(form, 'ssl_interval_seconds', settings.ssl_interval_seconds ?? 300);
  setFormFieldValue(form, 'ssl_timeout_seconds', settings.ssl_timeout_seconds ?? 5);

  if (stats) {
    const items = [
      ['Последний ping scheduler', formatTs(settings.last_ping_scheduler_run_at)],
      ['Последний SSH scheduler', formatTs(settings.last_ssh_scheduler_run_at)],
      ['Последний HTTP scheduler', formatTs(settings.last_http_scheduler_run_at)],
      ['Последний 3x-ui scheduler', formatTs(settings.last_xui_scheduler_run_at)],
      ['Ping / SSH / HTTP / 3x-ui интервалы', `${settings.ping_interval_seconds}s / ${settings.ssh_interval_seconds}s / ${settings.http_interval_seconds}s / ${settings.xui_interval_seconds}s`],
      ['Ping / SSH / HTTP / 3x-ui таймауты', `${settings.ping_timeout_seconds}s / ${settings.tcp_timeout_seconds}s / ${settings.http_timeout_seconds}s / ${settings.xui_timeout_seconds}s`],
    ];
    stats.innerHTML = items.map(([label, value]) => `
      <div class="micro-stat">
        <div class="label">${safe(label)}</div>
        <strong>${safe(value)}</strong>
      </div>
    `).join('');
  }
}

function renderProbeHistory(items) {
  const body = $('probeHistoryRows');
  if (!body) return;
  const rows = items || [];
  setText('probeHistoryCountLabel', `${rows.length} записей`);
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">История прогонов пока пуста. После scheduler/manual запусков здесь появятся записи.</td></tr>';
    return;
  }

  body.innerHTML = rows.map((item) => {
    const resultHtml = item.ok === true
      ? '<span class="pill pill-success">OK</span>'
      : item.ok === false
        ? '<span class="pill pill-danger">FAIL</span>'
        : '<span class="pill pill-neutral">unknown</span>';
    const details = [];
    if (item.details) details.push(String(item.details));
    if (item.latency_ms !== null && item.latency_ms !== undefined) details.push(`${item.latency_ms} ms`);
    if (item.status_code !== null && item.status_code !== undefined) details.push(`HTTP ${item.status_code}`);
    return `
      <tr>
        <td>${formatTs(item.started_at)}</td>
        <td><span class="pill ${item.source === 'scheduler' ? 'pill-info' : 'pill-neutral'}">${safe(item.source)}</span></td>
        <td>${safe(item.probe_type)}</td>
        <td><strong>${safe(item.server_name)}</strong><br><span class="code-text">${safe(item.server_host)}</span></td>
        <td>${resultHtml}</td>
        <td>${details.length ? safe(details.join(' · ')) : '—'}</td>
        <td><div class="error-snippet" title="${safe(item.error || '')}">${safe(truncateText(item.error || '—', 120))}</div></td>
      </tr>
    `;
  }).join('');
}

function renderAlertSettings(settings) {
  const form = $('alertSettingsForm');
  const stats = $('alertChannelStats');
  if (!form || !settings) return;
  setFormFieldChecked(form, 'notifications_enabled', settings.notifications_enabled);
  setFormFieldChecked(form, 'notify_on_new_alert', settings.notify_on_new_alert);
  setFormFieldChecked(form, 'notify_on_resolved', settings.notify_on_resolved);
  setFormFieldChecked(form, 'stale_alert_enabled', settings.stale_alert_enabled);
  setFormFieldValue(form, 'stale_after_seconds', settings.stale_after_seconds ?? 900);
  setFormFieldValue(form, 'reminder_interval_seconds', settings.reminder_interval_seconds ?? 3600);
  if (stats) {
    const items = [
      ['Telegram', settings.telegram_configured ? `configured → ${settings.telegram_target || 'chat'}` : 'not configured'],
      ['Email', settings.email_configured ? `configured → ${settings.email_target || 'mailbox'}` : 'not configured'],
      ['Stale threshold', `${settings.stale_after_seconds}s`],
      ['Reminder interval', `${settings.reminder_interval_seconds}s`],
    ];
    stats.innerHTML = items.map(([label, value]) => `
      <div class="micro-stat">
        <div class="label">${safe(label)}</div>
        <strong>${safe(value)}</strong>
      </div>
    `).join('');
  }
}

function renderAlertDeliveries(items) {
  const body = $('alertDeliveryRows');
  if (!body) return;
  const rows = items || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">Журнал доставок пока пуст. После alert-уведомлений здесь появятся записи.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((item) => `
    <tr>
      <td>${formatTs(item.created_at)}</td>
      <td><span class="pill pill-neutral">${safe(item.channel)}</span></td>
      <td>${safe(item.event_type)}</td>
      <td><strong>${safe(item.server_name_snapshot || 'system')}</strong><br><span class="code-text">${safe(item.server_host_snapshot || item.target || '—')}</span></td>
      <td>${item.status === 'sent' ? '<span class="pill pill-success">sent</span>' : item.status === 'failed' ? '<span class="pill pill-danger">failed</span>' : '<span class="pill pill-warning">skipped</span>'}</td>
      <td title="${safe(item.message || '')}">${safe(truncateText(item.message || '—', 70))}</td>
      <td><div class="error-snippet" title="${safe(item.error || '')}">${safe(truncateText(item.error || '—', 120))}</div></td>
    </tr>
  `).join('');
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
    ['SSH OK', summary.ssh_ok_total, 'tcp'],
    ['HTTP OK', summary.http_ok_total, 'web'],
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
    ['Проблемы по ping', summary.ping_fail_total],
    ['Проблемы по SSH', summary.ssh_fail_total],
    ['Проблемы по HTTP', summary.http_fail_total],
    ['Активные alerts', summary.active_alerts_total],
  ].map(([label, value]) => `
    <div class="micro-stat">
      <div class="label">${safe(label)}</div>
      <strong>${safe(value)}</strong>
    </div>
  `).join('');
}

function serverMatches(server, query) {
  if (!query) return true;
  const text = [server.name, server.host, server.ssh_user, server.web_url, server.description, ...(server.groups || [])]
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
      <td>${formatLatency(item.ping_latency_ms)}</td>
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
          <td>${safe(item.message)}<div class="muted small-text">notify=${safe(item.notify_count)} · last=${formatTs(item.last_notified_at)}</div></td>
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
  const filtered = applyServerFilter((servers || []).filter((item) => serverMatches(item, state.serverSearch)));
  setText('serversCountLabel', `${filtered.length} серверов`);

  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty-cell">Серверы не найдены. Можно создать первый сервер или сбросить фильтр.</td></tr>';
    return;
  }

  body.innerHTML = filtered.map((item) => {
    const st = statusMap.get(String(item.id)) || {};
    const contourDetails = buildContourDetails(st);
    const groups = (item.groups || []).length
      ? `<div class="inline-pills">${item.groups.map((g) => `<span class="pill pill-neutral">${safe(g)}</span>`).join('')}</div>`
      : '<span class="muted">—</span>';
    const errorSnippet = st.last_error ? `<div class="error-snippet" title="${safe(st.last_error)}">${safe(truncateText(st.last_error, 92))}</div>` : '<div class="muted small-text">Ошибок не зафиксировано</div>';
    const webText = item.web_url ? safe(item.web_url) : '—';
    return `
      <tr>
        <td>
          <strong>${safe(item.name)}</strong><br>
          <span class="code-text">${safe(item.host)}</span>
        </td>
        <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
        <td>${groups}</td>
        <td>
          <div class="status-pill-row">
            ${statusPillHtml('Ping', st.ping_ok)}
            ${statusPillHtml('SSH', st.ssh_ok)}
            ${statusPillHtml('HTTP', item.has_http_monitoring ? st.http_ok : null, item.has_http_monitoring ? null : 'off')}
            ${statusPillHtml('3x-ui console', item.has_3xui ? st.console_3xui_ok : null, item.has_3xui ? null : 'off')}
            ${statusPillHtml('3x-ui sub', item.has_3xui ? st.subscription_3xui_ok : null, item.has_3xui ? null : 'off')}
          </div>
          <div class="muted small-text">web: ${webText}</div>
          <div class="muted small-text">console: ${item.console_3xui_url ? safe(item.console_3xui_url) : '—'}${contourDetails.console ? ` · ${safe(contourDetails.console)}` : ''}</div>
          <div class="muted small-text">subscription: ${item.subscription_3xui_url ? safe(item.subscription_3xui_url) : '—'}${contourDetails.sub ? ` · ${safe(contourDetails.sub)}` : ''}</div>
          <div class="muted small-text">ssl: ${contourDetails.ssl ? safe(contourDetails.ssl) : '—'}</div>
        </td>
        <td>
          <div>${formatTs(st.last_check_at)}</div>
          ${errorSnippet}
        </td>
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
  const filtered = applyServerFilter((items || []).filter((item) => serverMatches(item, state.serverSearch)));
  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="12" class="empty-cell">Серверы не найдены. Добавьте их в inventory.</td></tr>';
    return;
  }
  body.innerHTML = filtered.map((item) => {
    const groupText = (item.groups || []).map((g) => safe(g)).join(', ') || 'Без группы';
    const contourDetails = buildContourDetails(item);
    const probePills = [
      probeBadgeHtml('HTTP', item.http_ok, { disabled: !item.has_http_monitoring, detail: contourDetails.http || (item.http_status_code ? `HTTP ${item.http_status_code}` : ''), hoverOnly: true }),
      probeBadgeHtml('3x-ui console', item.console_3xui_ok, { disabled: !item.has_3xui, detail: contourDetails.console || (item.console_3xui_http_status ? `HTTP ${item.console_3xui_http_status}` : ''), hoverOnly: true }),
      probeBadgeHtml('3x-ui sub', item.subscription_3xui_ok, { disabled: !item.has_3xui, detail: contourDetails.sub || (item.subscription_3xui_http_status ? `HTTP ${item.subscription_3xui_http_status}` : ''), hoverOnly: true }),
      probeBadgeHtml('SSL', item.ssl_ok, { disabled: !item.has_ssl_monitoring, detail: contourDetails.ssl || '', hoverOnly: true })
    ].join('');

    const latencyPills = [
      latencyBadgeHtml('ping', item.ping_latency_ms),
      latencyBadgeHtml('ssh', item.ssh_latency_ms),
      latencyBadgeHtml('http', item.http_response_ms),
      latencyBadgeHtml('3x-ui console', item.console_3xui_response_ms),
      latencyBadgeHtml('3x-ui sub', item.subscription_3xui_response_ms)
    ].join('');

    return `
      <tr>
        <td>${safe(item.id)}</td>
        <td><strong>${safe(item.name)}</strong><div class="muted small-text clamp-2">${groupText}</div></td>
        <td><span class="code-text">${safe(item.host)}</span></td>
        <td><span class="code-text">${safe(item.ssh_user)}:${safe(item.ssh_port)}</span></td>
        <td>${compactUrlHtml(item.web_url, 'не задан')}</td>
        <td>${statusHtml(item.ping_ok)}</td>
        <td>${statusHtml(item.ssh_ok)}</td>
        <td><div class="status-badge-stack">${probePills}</div></td>
        <td><div class="metric-pill-stack">${latencyPills}</div></td>
        <td>${Number(item.active_alerts || 0) > 0 ? `<span class="pill pill-danger">${safe(item.active_alerts)}</span>` : '<span class="pill pill-success">0</span>'}</td>
        <td><span class="date-chip">${formatTs(item.last_check_at)}</span></td>
        <td><span class="cell-soft">${errorCellHtml(item.last_error)}</span></td>
      </tr>
    `;
  }).join('');
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
  renderSidebarOverview(state.summary);
  renderSummary(state.summary);
  renderChecksQuickStats(state.summary);
  renderMonitorSettings(state.monitorSettings);
  renderAlertSettings(state.alertSettings);
  renderProbeHistory(state.probeHistory || []);
  renderAlertDeliveries(state.alertDeliveries || []);
  renderDashboardServers(state.statuses || []);
  renderAlerts(state.alerts || []);
  renderServersTable(state.servers || [], state.statuses || []);
  renderGroups(state.groups || []);
  renderGroupLinks(state.groupLinks || []);
  renderStatuses(state.statuses || []);
  qa('#serverFilterBar .filter-chip').forEach((node) => node.classList.toggle('active', node.dataset.filter === state.serverFilter));
  populateSelect('attachGroupSelect', state.groups || [], 'Сначала создайте группу', (g) => `${g.name} (#${g.id})`);
  populateSelect('attachServerSelect', state.servers || [], 'Сначала добавьте сервер', (s) => `${s.name} (${s.host})`);
}

async function loadAll() {
  const [version, summary, servers, groups, statuses, alerts, groupLinks, monitorSettings, alertSettings, alertDeliveries, probeHistory] = await Promise.all([
    fetchJson(endpoints.version),
    fetchJson(endpoints.summary),
    fetchJson(endpoints.servers),
    fetchJson(endpoints.groups),
    fetchJson(endpoints.statuses),
    fetchJson(endpoints.alerts),
    fetchJson(endpoints.groupLinks),
    fetchJson(endpoints.monitorSettings),
    fetchJson(endpoints.alertSettings),
    fetchJson(endpoints.alertDeliveries),
    fetchJson(endpoints.probeHistory),
  ]);
  state.version = version;
  state.summary = summary;
  state.servers = servers;
  state.groups = groups;
  state.statuses = statuses;
  state.alerts = alerts;
  state.groupLinks = groupLinks;
  state.monitorSettings = monitorSettings;
  state.alertSettings = alertSettings;
  state.alertDeliveries = alertDeliveries;
  state.probeHistory = probeHistory;
  state.lastLoadedAt = new Date().toISOString();
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
  form.web_url.value = server.web_url || '';
  form.console_3xui_url.value = server.console_3xui_url || '';
  form.subscription_3xui_url.value = server.subscription_3xui_url || '';
  form.description.value = server.description || '';
  form.is_enabled.checked = !!server.is_enabled;
  form.has_http_monitoring.checked = !!server.has_http_monitoring;
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
  form.web_url.value = '';
  form.is_enabled.checked = true;
  form.has_http_monitoring.checked = false;
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
    web_url: form.web_url.value.trim() || null,
    console_3xui_url: form.console_3xui_url.value.trim() || null,
    subscription_3xui_url: form.subscription_3xui_url.value.trim() || null,
    description: form.description.value.trim() || null,
    is_enabled: form.is_enabled.checked,
    has_http_monitoring: form.has_http_monitoring.checked,
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

    if (Number(result.failed || 0) > 0) {
      const firstFailed = Array.isArray(result.results) ? result.results.find((item) => !item.ok) : null;
      let details = firstFailed?.error || firstFailed?.persistence_error || 'подробности не получены';
      try {
        const diag = await fetchJson(endpoints.pingDiagnostics);
        if (diag?.self_test?.ok === false && diag?.self_test?.error) {
          details += `; self-test: ${diag.self_test.error}`;
        } else if (diag?.binary_found === false) {
          details += '; ping binary не найден в контейнере';
        }
      } catch (diagError) {
        details += `; diagnostics: ${diagError.message}`;
      }
      showMessage('warning', `Ping probe завершён с ошибками: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}. Первая ошибка: ${details}`);
    } else {
      showMessage('success', `Ping probe завершён: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}`);
    }

    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить ping probe: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}


async function runSshProbe() {
  const buttons = ['sshBtnChecks', 'allChecksBtn'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.sshRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tcp_timeout_seconds: 3, http_timeout_seconds: 5 }),
    });
    showMessage('success', `SSH probe завершён: processed=${result.processed}, ok=${result.ok}, failed=${result.failed}`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить SSH probe: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function runHttpProbe() {
  const buttons = ['httpBtnChecks', 'allChecksBtn'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.httpRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tcp_timeout_seconds: 3, http_timeout_seconds: 5, xui_timeout_seconds: 5 }),
    });
    showMessage('success', `HTTP/HTTPS probe завершён: http ok=${result.ok}, http fail=${result.failed}, 3x-ui ok=${result.xui_ok}, 3x-ui fail=${result.xui_failed}, skipped=${result.skipped + result.xui_skipped}`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить HTTP/HTTPS probe: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function runXuiProbe() {
  const buttons = ['xuiBtnChecks', 'allChecksBtn'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.xuiRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ xui_timeout_seconds: 5 }),
    });
    showMessage('success', `Проверка 3x-ui завершена.`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить проверку 3x-ui: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function runSslProbe() {
  const buttons = ['sslBtnChecks', 'allChecksBtn'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.sslRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ssl_timeout_seconds: 5 }),
    });
    showMessage('success', `Проверка SSL завершена.`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить проверку SSL: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function runAllChecks() {
  const buttons = ['allChecksBtn', 'pingBtnChecks', 'sshBtnChecks', 'httpBtnChecks', 'xuiBtnChecks', 'sslBtnChecks', 'pingBtn'].map($).filter(Boolean);
  buttons.forEach((btn) => { btn.disabled = true; });
  try {
    const result = await fetchJson(endpoints.allRun, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tcp_timeout_seconds: 3, http_timeout_seconds: 5, xui_timeout_seconds: 5, ssl_timeout_seconds: 5 }),
    });
    showMessage('success', `Все проверки завершены: ping=${result.ping.failed} fail, ssh=${result.ssh.failed} fail, http=${result.http.failed} fail, 3x-ui=${result.xui.failed} fail, ssl=${result.ssl.failed} fail`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось запустить все проверки: ${error.message}`);
  } finally {
    buttons.forEach((btn) => { btn.disabled = false; });
  }
}

async function handleMonitorSettingsSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    scheduler_enabled: form.scheduler_enabled.checked,
    ping_interval_seconds: Number(form.ping_interval_seconds.value || 60),
    ssh_interval_seconds: Number(form.ssh_interval_seconds.value || 120),
    http_interval_seconds: Number(form.http_interval_seconds.value || 180),
    ping_timeout_seconds: Number(form.ping_timeout_seconds.value || 2),
    tcp_timeout_seconds: Number(form.tcp_timeout_seconds.value || 3),
    http_timeout_seconds: Number(form.http_timeout_seconds.value || 5),
    xui_interval_seconds: Number(form.xui_interval_seconds.value || 240),
    xui_timeout_seconds: Number(form.xui_timeout_seconds.value || 5),
    ssl_interval_seconds: Number(form.ssl_interval_seconds.value || 300),
    ssl_timeout_seconds: Number(form.ssl_timeout_seconds.value || 5),
  };
  const submitBtn = $('monitorSettingsSubmitBtn');
  if (submitBtn) submitBtn.disabled = true;
  try {
    const result = await fetchJson(endpoints.monitorSettings, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    state.monitorSettings = result;
    renderMonitorSettings(state.monitorSettings);
    showMessage('success', `Настройки мониторинга сохранены. Планировщик ${result.scheduler_enabled ? 'включён' : 'выключен'}.`);
    await loadAll();
    setTab('checks');
  } catch (error) {
    showMessage('error', `Не удалось сохранить настройки мониторинга: ${error.message}`);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function handleAlertSettingsSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    notifications_enabled: form.notifications_enabled.checked,
    notify_on_new_alert: form.notify_on_new_alert.checked,
    notify_on_resolved: form.notify_on_resolved.checked,
    stale_alert_enabled: form.stale_alert_enabled.checked,
    stale_after_seconds: Number(form.stale_after_seconds.value || 900),
    reminder_interval_seconds: Number(form.reminder_interval_seconds.value || 3600),
  };
  const submitBtn = $('alertSettingsSubmitBtn');
  if (submitBtn) submitBtn.disabled = true;
  try {
    const result = await fetchJson(endpoints.alertSettings, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    state.alertSettings = result;
    renderAlertSettings(result);
    showMessage('success', `Настройки alerting сохранены. Уведомления ${result.notifications_enabled ? 'включены' : 'выключены'}.`);
    await loadAll();
    setTab('alerts');
  } catch (error) {
    showMessage('error', `Не удалось сохранить настройки alerting: ${error.message}`);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function sendTestAlert() {
  const btn = $('alertTestBtn');
  if (btn) btn.disabled = true;
  try {
    const result = await fetchJson(endpoints.alertTest, { method: 'POST' });
    showMessage(result.sent > 0 ? 'success' : 'warning', `Тестовое уведомление: sent=${result.sent || 0}, failed=${result.failed || 0}, skipped=${result.skipped || 0}`);
    await loadAll();
    setTab('alerts');
  } catch (error) {
    showMessage('error', `Не удалось отправить тестовое уведомление: ${error.message}`);
  } finally {
    if (btn) btn.disabled = false;
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
  $('pingBtn')?.addEventListener('click', runAllChecks);
  $('pingBtnChecks')?.addEventListener('click', runPingProbe);
  $('sshBtnChecks')?.addEventListener('click', runSshProbe);
  $('httpBtnChecks')?.addEventListener('click', runHttpProbe);
  $('xuiBtnChecks')?.addEventListener('click', runXuiProbe);
  $('sslBtnChecks')?.addEventListener('click', runSslProbe);
  $('allChecksBtn')?.addEventListener('click', runAllChecks);
  $('serverForm')?.addEventListener('submit', handleServerSubmit);
  $('groupForm')?.addEventListener('submit', handleGroupSubmit);
  $('attachForm')?.addEventListener('submit', handleAttachSubmit);
  $('monitorSettingsForm')?.addEventListener('submit', handleMonitorSettingsSubmit);
  $('alertSettingsForm')?.addEventListener('submit', handleAlertSettingsSubmit);
  $('alertTestBtn')?.addEventListener('click', sendTestAlert);
  $('serverCancelBtn')?.addEventListener('click', resetServerForm);
  $('groupCancelBtn')?.addEventListener('click', resetGroupForm);
  $('serverSearchInput')?.addEventListener('input', (e) => { state.serverSearch = e.target.value.trim().toLowerCase(); refreshUi(); });
  $('groupSearchInput')?.addEventListener('input', (e) => { state.groupSearch = e.target.value.trim().toLowerCase(); refreshUi(); });
  qa('#serverFilterBar .filter-chip').forEach((node) => node.addEventListener('click', () => {
    state.serverFilter = node.dataset.filter || 'all';
    refreshUi();
  }));
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
