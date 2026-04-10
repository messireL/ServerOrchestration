from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.db import (
    attach_server_to_group,
    create_group,
    create_server,
    get_summary,
    init_db,
    list_active_alerts,
    list_enabled_servers,
    list_groups,
    list_server_status,
    list_servers,
    ping_db,
    resolve_alert,
    set_alert_active,
    update_ping_status,
)
from src.probes import run_ping

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_VERSION = os.getenv("APP_VERSION", "0.1.4")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")

UI_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>ServerOrchestration</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background:#0f172a; color:#e2e8f0; }
    h1,h2 { margin: 0 0 12px; }
    .row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:16px; }
    .card { background:#111827; border:1px solid #334155; border-radius:14px; padding:16px; min-width:220px; box-shadow:0 6px 20px rgba(0,0,0,.25); }
    .wide { width:100%; }
    .muted { color:#94a3b8; font-size:14px; }
    button { background:#2563eb; color:white; border:none; border-radius:10px; padding:10px 14px; cursor:pointer; }
    button:disabled { background:#475569; cursor:not-allowed; }
    table { width:100%; border-collapse:collapse; }
    th, td { text-align:left; padding:10px; border-bottom:1px solid #334155; vertical-align:top; }
    th { color:#93c5fd; font-weight:600; }
    .ok { color:#22c55e; font-weight:700; }
    .bad { color:#ef4444; font-weight:700; }
    .na { color:#f59e0b; font-weight:700; }
    .toolbar { display:flex; gap:12px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }
    code { background:#020617; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <div class="toolbar">
    <h1>ServerOrchestration</h1>
    <button id="refreshBtn">Обновить</button>
    <button id="pingBtn">Запустить ping probe</button>
    <span class="muted">Версия: <code id="version">—</code></span>
  </div>

  <div class="row" id="summaryCards"></div>

  <div class="row">
    <div class="card wide">
      <h2>Статусы серверов</h2>
      <div class="muted" style="margin-bottom:10px;">Список серверов пока только для просмотра. Ввод серверов через отдельный web-интерфейс добавим следующим этапом.</div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Сервер</th>
            <th>Host</th>
            <th>Группы</th>
            <th>Ping</th>
            <th>Latency</th>
            <th>Alerts</th>
            <th>Последняя проверка</th>
            <th>Ошибка</th>
          </tr>
        </thead>
        <tbody id="statusRows"></tbody>
      </table>
    </div>
  </div>

  <div class="row">
    <div class="card wide">
      <h2>Активные alerts</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Сервер</th>
            <th>Тип</th>
            <th>Severity</th>
            <th>Сообщение</th>
            <th>Впервые</th>
            <th>Последнее событие</th>
          </tr>
        </thead>
        <tbody id="alertRows"></tbody>
      </table>
    </div>
  </div>

<script>
function badge(value) {
  if (value === true) return '<span class="ok">OK</span>';
  if (value === false) return '<span class="bad">FAIL</span>';
  return '<span class="na">N/A</span>';
}

function safe(text) {
  if (text === null || text === undefined || text === '') return '—';
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function renderSummary(summary) {
  const cards = [
    ['Всего серверов', summary.servers_total],
    ['Включено', summary.servers_enabled],
    ['Групп', summary.groups_total],
    ['Связей сервер-группа', summary.group_links_total],
    ['Ping OK', summary.ping_ok_total],
    ['Ping FAIL', summary.ping_fail_total],
    ['Ping unknown', summary.ping_unknown_total],
    ['Активные alerts', summary.active_alerts_total],
  ];
  document.getElementById('summaryCards').innerHTML = cards
    .map(([title, value]) => `<div class="card"><div class="muted">${safe(title)}</div><div style="font-size:28px;font-weight:700;margin-top:8px;">${safe(value)}</div></div>`)
    .join('');
}

function renderStatuses(items) {
  const rows = items.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td>${safe(item.name)}</td>
      <td>${safe(item.host)}</td>
      <td>${safe((item.groups || []).join(', '))}</td>
      <td>${badge(item.ping_ok)}</td>
      <td>${safe(item.ping_latency_ms)}</td>
      <td>${safe(item.active_alerts)}</td>
      <td>${safe(item.last_check_at)}</td>
      <td>${safe(item.last_error)}</td>
    </tr>
  `).join('');
  document.getElementById('statusRows').innerHTML = rows || '<tr><td colspan="9" class="muted">Серверы ещё не добавлены.</td></tr>';
}

function renderAlerts(items) {
  const rows = items.map(item => `
    <tr>
      <td>${safe(item.id)}</td>
      <td>${safe(item.server_name)}<br><span class="muted">${safe(item.server_host)}</span></td>
      <td>${safe(item.alert_type)}</td>
      <td>${safe(item.severity)}</td>
      <td>${safe(item.message)}</td>
      <td>${safe(item.first_seen_at)}</td>
      <td>${safe(item.last_seen_at)}</td>
    </tr>
  `).join('');
  document.getElementById('alertRows').innerHTML = rows || '<tr><td colspan="7" class="muted">Активных alerts пока нет.</td></tr>';
}

async function loadDashboard() {
  const [versionRes, summaryRes, statusRes, alertsRes] = await Promise.all([
    fetch('/version'),
    fetch('/api/summary'),
    fetch('/api/status/servers'),
    fetch('/api/alerts'),
  ]);

  const version = await versionRes.json();
  const summary = await summaryRes.json();
  const statuses = await statusRes.json();
  const alerts = await alertsRes.json();

  document.getElementById('version').textContent = version.version + ' / ' + version.timezone;
  renderSummary(summary);
  renderStatuses(statuses);
  renderAlerts(alerts);
}

async function runPingProbe() {
  const pingBtn = document.getElementById('pingBtn');
  pingBtn.disabled = true;
  try {
    const res = await fetch('/api/probes/ping/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timeout_seconds: 2 }),
    });
    const data = await res.json();
    alert('Ping probe завершён: processed=' + data.processed + ', ok=' + data.ok + ', failed=' + data.failed);
    await loadDashboard();
  } catch (err) {
    alert('Ошибка запуска ping probe: ' + err);
  } finally {
    pingBtn.disabled = false;
  }
}

document.getElementById('refreshBtn').addEventListener('click', loadDashboard);
document.getElementById('pingBtn').addEventListener('click', runPingProbe);
loadDashboard();
</script>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Server Orchestration API",
    version=APP_VERSION,
    lifespan=lifespan,
)


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="root", min_length=1, max_length=100)
    description: Optional[str] = None
    is_enabled: bool = True
    has_3xui: bool = False
    has_ssl_monitoring: bool = False


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class PingProbeRequest(BaseModel):
    timeout_seconds: int = Field(default=2, ge=1, le=10)


@app.get("/", response_class=HTMLResponse)
def root():
    return UI_HTML


@app.get("/health")
def health():
    db_ok = False
    try:
        db_ok = ping_db()
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "service": APP_NAME,
        "version": APP_VERSION,
        "database": db_ok,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/version")
def version():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "timezone": APP_TZ,
    }


@app.get("/api/summary")
def api_summary():
    return get_summary()


@app.get("/api/servers")
def api_list_servers():
    return list_servers()


@app.get("/api/status/servers")
def api_list_server_status():
    return list_server_status()


@app.post("/api/servers")
def api_create_server(payload: ServerCreate):
    try:
        return create_server(
            name=payload.name,
            host=payload.host,
            ssh_port=payload.ssh_port,
            ssh_user=payload.ssh_user,
            description=payload.description,
            is_enabled=payload.is_enabled,
            has_3xui=payload.has_3xui,
            has_ssl_monitoring=payload.has_ssl_monitoring,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/groups")
def api_list_groups():
    return list_groups()


@app.post("/api/groups")
def api_create_group(payload: GroupCreate):
    try:
        return create_group(
            name=payload.name,
            description=payload.description,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/groups/{group_id}/servers/{server_id}")
def api_attach_server_to_group(group_id: int, server_id: int):
    try:
        return attach_server_to_group(group_id=group_id, server_id=server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/alerts")
def api_list_active_alerts():
    return list_active_alerts()


@app.post("/api/probes/ping/run")
def api_run_ping_probe(payload: PingProbeRequest):
    enabled_servers = list_enabled_servers()

    processed = 0
    ok_count = 0
    failed_count = 0
    results = []

    for server in enabled_servers:
        processed += 1
        probe = run_ping(server["host"], timeout_seconds=payload.timeout_seconds)
        update_ping_status(
            server_id=server["id"],
            ping_ok=probe["ok"],
            ping_latency_ms=probe["latency_ms"],
            error=probe["error"],
        )

        if probe["ok"]:
            ok_count += 1
            resolve_alert(server_id=server["id"], alert_type="ping_down")
        else:
            failed_count += 1
            set_alert_active(
                server_id=server["id"],
                alert_type="ping_down",
                severity="critical",
                message=f"Ping check failed for {server['name']} ({server['host']}): {probe['error'] or 'unknown error'}",
            )

        results.append(
            {
                "server_id": server["id"],
                "server_name": server["name"],
                "host": server["host"],
                "ping_ok": probe["ok"],
                "ping_latency_ms": probe["latency_ms"],
                "error": probe["error"],
            }
        )

    return {
        "processed": processed,
        "ok": ok_count,
        "failed": failed_count,
        "results": results,
    }
