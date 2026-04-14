import os
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def get_conn():
    return connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "orchestrator"),
        user=os.getenv("DB_USER", "orchestrator"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


def ping_db() -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
            return bool(row and row["ok"] == 1)


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS server_groups (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS servers (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    host TEXT NOT NULL,
                    ssh_port INTEGER NOT NULL DEFAULT 22,
                    ssh_user TEXT NOT NULL DEFAULT 'srvops',
                    web_url TEXT,
                    console_3xui_url TEXT,
                    subscription_3xui_url TEXT,
                    description TEXT,
                    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    has_3xui BOOLEAN NOT NULL DEFAULT FALSE,
                    has_ssl_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
                    has_http_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE servers ALTER COLUMN ssh_user SET DEFAULT 'srvops';")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS web_url TEXT;")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS console_3xui_url TEXT;")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS subscription_3xui_url TEXT;")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS has_3xui BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS has_ssl_monitoring BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS has_http_monitoring BOOLEAN NOT NULL DEFAULT FALSE;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS server_group_members (
                    group_id BIGINT NOT NULL REFERENCES server_groups(id) ON DELETE CASCADE,
                    server_id BIGINT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (group_id, server_id)
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS server_status (
                    server_id BIGINT PRIMARY KEY REFERENCES servers(id) ON DELETE CASCADE,
                    ping_ok BOOLEAN,
                    ping_latency_ms INTEGER,
                    ssh_ok BOOLEAN,
                    ssh_latency_ms INTEGER,
                    http_ok BOOLEAN,
                    http_status_code INTEGER,
                    http_response_ms INTEGER,
                    console_3xui_ok BOOLEAN,
                    console_3xui_http_status INTEGER,
                    console_3xui_response_ms INTEGER,
                    subscription_3xui_ok BOOLEAN,
                    subscription_3xui_http_status INTEGER,
                    subscription_3xui_response_ms INTEGER,
                    ssl_ok BOOLEAN,
                    reboot_required BOOLEAN,
                    last_error TEXT,
                    last_check_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );
                """
            )
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS ping_latency_ms INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS ssh_ok BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS ssh_latency_ms INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS http_ok BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS http_status_code INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS http_response_ms INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS console_3xui_ok BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS console_3xui_http_status INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS console_3xui_response_ms INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS subscription_3xui_ok BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS subscription_3xui_http_status INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS subscription_3xui_response_ms INTEGER;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS ssl_ok BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS reboot_required BOOLEAN;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS last_error TEXT;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS last_check_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS summary_json JSONB NOT NULL DEFAULT '{}'::jsonb;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id BIGSERIAL PRIMARY KEY,
                    server_id BIGINT REFERENCES servers(id) ON DELETE CASCADE,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'warning',
                    status TEXT NOT NULL DEFAULT 'active',
                    message TEXT NOT NULL,
                    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alerts_server_status
                ON alerts(server_id, status, alert_type);
                """
            )
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS notify_count INTEGER NOT NULL DEFAULT 0;")
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_delivery_status TEXT;")
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_delivery_error TEXT;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_settings (
                    id SMALLINT PRIMARY KEY CHECK (id = 1),
                    notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    notify_on_new_alert BOOLEAN NOT NULL DEFAULT TRUE,
                    notify_on_resolved BOOLEAN NOT NULL DEFAULT TRUE,
                    stale_alert_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    stale_after_seconds INTEGER NOT NULL DEFAULT 900,
                    reminder_interval_seconds INTEGER NOT NULL DEFAULT 3600,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS notify_on_new_alert BOOLEAN NOT NULL DEFAULT TRUE;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS notify_on_resolved BOOLEAN NOT NULL DEFAULT TRUE;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS stale_alert_enabled BOOLEAN NOT NULL DEFAULT TRUE;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS stale_after_seconds INTEGER NOT NULL DEFAULT 900;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS reminder_interval_seconds INTEGER NOT NULL DEFAULT 3600;")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("ALTER TABLE alert_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute(
                """
                INSERT INTO alert_settings (id)
                VALUES (1)
                ON CONFLICT (id) DO NOTHING;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_delivery_log (
                    id BIGSERIAL PRIMARY KEY,
                    alert_id BIGINT REFERENCES alerts(id) ON DELETE SET NULL,
                    server_id BIGINT REFERENCES servers(id) ON DELETE SET NULL,
                    server_name_snapshot TEXT,
                    server_host_snapshot TEXT,
                    alert_type TEXT,
                    event_type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    target TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alert_delivery_log_created_at
                ON alert_delivery_log(created_at DESC, id DESC);
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_settings (
                    id SMALLINT PRIMARY KEY CHECK (id = 1),
                    scheduler_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    ping_interval_seconds INTEGER NOT NULL DEFAULT 60,
                    ssh_interval_seconds INTEGER NOT NULL DEFAULT 120,
                    http_interval_seconds INTEGER NOT NULL DEFAULT 180,
                    xui_interval_seconds INTEGER NOT NULL DEFAULT 240,
                    ping_timeout_seconds INTEGER NOT NULL DEFAULT 2,
                    tcp_timeout_seconds INTEGER NOT NULL DEFAULT 3,
                    http_timeout_seconds INTEGER NOT NULL DEFAULT 5,
                    xui_timeout_seconds INTEGER NOT NULL DEFAULT 5,
                    last_ping_scheduler_run_at TIMESTAMPTZ,
                    last_ssh_scheduler_run_at TIMESTAMPTZ,
                    last_http_scheduler_run_at TIMESTAMPTZ,
                    last_xui_scheduler_run_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS scheduler_enabled BOOLEAN NOT NULL DEFAULT TRUE;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS ping_interval_seconds INTEGER NOT NULL DEFAULT 60;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS ssh_interval_seconds INTEGER NOT NULL DEFAULT 120;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS http_interval_seconds INTEGER NOT NULL DEFAULT 180;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS xui_interval_seconds INTEGER NOT NULL DEFAULT 240;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS ssl_interval_seconds INTEGER NOT NULL DEFAULT 300;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS ping_timeout_seconds INTEGER NOT NULL DEFAULT 2;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS tcp_timeout_seconds INTEGER NOT NULL DEFAULT 3;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS http_timeout_seconds INTEGER NOT NULL DEFAULT 5;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS xui_timeout_seconds INTEGER NOT NULL DEFAULT 5;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS ssl_timeout_seconds INTEGER NOT NULL DEFAULT 5;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS last_ping_scheduler_run_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS last_ssh_scheduler_run_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS last_http_scheduler_run_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS last_xui_scheduler_run_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS last_ssl_scheduler_run_at TIMESTAMPTZ;")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("ALTER TABLE monitor_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute(
                """
                INSERT INTO monitor_settings (id)
                VALUES (1)
                ON CONFLICT (id) DO NOTHING;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS probe_history (
                    id BIGSERIAL PRIMARY KEY,
                    server_id BIGINT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                    server_name_snapshot TEXT NOT NULL,
                    server_host_snapshot TEXT NOT NULL,
                    probe_type TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    ok BOOLEAN,
                    latency_ms INTEGER,
                    status_code INTEGER,
                    error TEXT,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS server_name_snapshot TEXT;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS server_host_snapshot TEXT;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS probe_type TEXT;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS ok BOOLEAN;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS latency_ms INTEGER;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS status_code INTEGER;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS error TEXT;")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("ALTER TABLE probe_history ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")
            cur.execute("UPDATE probe_history SET server_name_snapshot = COALESCE(server_name_snapshot, '') WHERE server_name_snapshot IS NULL;")
            cur.execute("UPDATE probe_history SET server_host_snapshot = COALESCE(server_host_snapshot, '') WHERE server_host_snapshot IS NULL;")
            cur.execute("UPDATE probe_history SET probe_type = COALESCE(probe_type, 'ping') WHERE probe_type IS NULL;")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_probe_history_started_at ON probe_history(started_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_probe_history_server_probe ON probe_history(server_id, probe_type, started_at DESC);")

        conn.commit()


def list_servers() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    s.host,
                    s.ssh_port,
                    s.ssh_user,
                    s.web_url,
                    s.console_3xui_url,
                    s.subscription_3xui_url,
                    s.description,
                    s.is_enabled,
                    s.has_3xui,
                    s.has_ssl_monitoring,
                    s.has_http_monitoring,
                    s.created_at,
                    s.updated_at,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.ssh_latency_ms,
                    st.http_ok,
                    st.http_status_code,
                    st.http_response_ms,
                    st.console_3xui_ok,
                    st.console_3xui_http_status,
                    st.console_3xui_response_ms,
                    st.subscription_3xui_ok,
                    st.subscription_3xui_http_status,
                    st.subscription_3xui_response_ms,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at AS status_updated_at,
                    COALESCE(
                        ARRAY_REMOVE(ARRAY_AGG(DISTINCT g.name), NULL),
                        ARRAY[]::TEXT[]
                    ) AS groups
                FROM servers s
                LEFT JOIN server_status st ON st.server_id = s.id
                LEFT JOIN server_group_members gm ON gm.server_id = s.id
                LEFT JOIN server_groups g ON g.id = gm.group_id
                GROUP BY
                    s.id,
                    st.server_id,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.ssh_latency_ms,
                    st.http_ok,
                    st.http_status_code,
                    st.http_response_ms,
                    st.console_3xui_ok,
                    st.console_3xui_http_status,
                    st.console_3xui_response_ms,
                    st.subscription_3xui_ok,
                    st.subscription_3xui_http_status,
                    st.subscription_3xui_response_ms,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at,
                    st.summary_json
                ORDER BY s.id;
                """
            )
            return cur.fetchall()


def list_server_status() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    s.host,
                    s.ssh_port,
                    s.ssh_user,
                    s.web_url,
                    s.is_enabled,
                    s.has_3xui,
                    s.has_ssl_monitoring,
                    s.has_http_monitoring,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.ssh_latency_ms,
                    st.http_ok,
                    st.http_status_code,
                    st.http_response_ms,
                    st.console_3xui_ok,
                    st.console_3xui_http_status,
                    st.console_3xui_response_ms,
                    st.subscription_3xui_ok,
                    st.subscription_3xui_http_status,
                    st.subscription_3xui_response_ms,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at,
                    st.summary_json,
                    COALESCE(
                        ARRAY_REMOVE(ARRAY_AGG(DISTINCT g.name), NULL),
                        ARRAY[]::TEXT[]
                    ) AS groups,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM alerts a
                        WHERE a.server_id = s.id AND a.status = 'active'
                    ) AS active_alerts
                FROM servers s
                LEFT JOIN server_status st ON st.server_id = s.id
                LEFT JOIN server_group_members gm ON gm.server_id = s.id
                LEFT JOIN server_groups g ON g.id = gm.group_id
                GROUP BY
                    s.id,
                    st.server_id,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.ssh_latency_ms,
                    st.http_ok,
                    st.http_status_code,
                    st.http_response_ms,
                    st.console_3xui_ok,
                    st.console_3xui_http_status,
                    st.console_3xui_response_ms,
                    st.subscription_3xui_ok,
                    st.subscription_3xui_http_status,
                    st.subscription_3xui_response_ms,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at,
                    st.summary_json
                ORDER BY s.id;
                """
            )
            return cur.fetchall()


def create_server(name: str, host: str, ssh_port: int, ssh_user: str, web_url: str | None, console_3xui_url: str | None, subscription_3xui_url: str | None, description: str | None, is_enabled: bool, has_3xui: bool, has_ssl_monitoring: bool, has_http_monitoring: bool):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO servers
                    (name, host, ssh_port, ssh_user, web_url, console_3xui_url, subscription_3xui_url, description, is_enabled, has_3xui, has_ssl_monitoring, has_http_monitoring)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (name, host, ssh_port, ssh_user, web_url, console_3xui_url, subscription_3xui_url, description, is_enabled, has_3xui, has_ssl_monitoring, has_http_monitoring),
            )
            row = cur.fetchone()
            cur.execute("INSERT INTO server_status (server_id) VALUES (%s) ON CONFLICT (server_id) DO NOTHING;", (row["id"],))
        conn.commit()
        return row


def update_server(server_id: int, name: str, host: str, ssh_port: int, ssh_user: str, web_url: str | None, console_3xui_url: str | None, subscription_3xui_url: str | None, description: str | None, is_enabled: bool, has_3xui: bool, has_ssl_monitoring: bool, has_http_monitoring: bool):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE servers
                SET
                    name = %s,
                    host = %s,
                    ssh_port = %s,
                    ssh_user = %s,
                    web_url = %s,
                    console_3xui_url = %s,
                    subscription_3xui_url = %s,
                    description = %s,
                    is_enabled = %s,
                    has_3xui = %s,
                    has_ssl_monitoring = %s,
                    has_http_monitoring = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *;
                """,
                (name, host, ssh_port, ssh_user, web_url, console_3xui_url, subscription_3xui_url, description, is_enabled, has_3xui, has_ssl_monitoring, has_http_monitoring, server_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Сервер #{server_id} не найден")
        conn.commit()
        return row


def delete_server(server_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM servers WHERE id = %s RETURNING id, name;", (server_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Сервер #{server_id} не найден")
        conn.commit()
        return {"id": row["id"], "name": row["name"], "deleted": True}


def list_groups() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    g.id,
                    g.name,
                    g.description,
                    g.created_at,
                    COUNT(m.server_id)::INTEGER AS server_count
                FROM server_groups g
                LEFT JOIN server_group_members m ON m.group_id = g.id
                GROUP BY g.id
                ORDER BY g.id;
                """
            )
            return cur.fetchall()


def create_group(name: str, description: str | None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO server_groups (name, description) VALUES (%s, %s) RETURNING *;", (name, description))
            row = cur.fetchone()
        conn.commit()
        return row


def update_group(group_id: int, name: str, description: str | None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE server_groups SET name = %s, description = %s WHERE id = %s RETURNING *;", (name, description, group_id))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Группа #{group_id} не найдена")
        conn.commit()
        return row


def delete_group(group_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM server_groups WHERE id = %s RETURNING id, name;", (group_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Группа #{group_id} не найдена")
        conn.commit()
        return {"id": row["id"], "name": row["name"], "deleted": True}


def attach_server_to_group(group_id: int, server_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO server_group_members (group_id, server_id) VALUES (%s, %s) ON CONFLICT (group_id, server_id) DO NOTHING;", (group_id, server_id))
        conn.commit()
    return {"group_id": group_id, "server_id": server_id, "linked": True}


def detach_server_from_group(group_id: int, server_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM server_group_members WHERE group_id = %s AND server_id = %s RETURNING group_id, server_id;", (group_id, server_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Связь сервер↔группа не найдена")
        conn.commit()
    return {"group_id": row["group_id"], "server_id": row["server_id"], "deleted": True}


def list_group_links() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    gm.group_id,
                    gm.server_id,
                    g.name AS group_name,
                    s.name AS server_name,
                    s.host AS server_host,
                    gm.created_at
                FROM server_group_members gm
                JOIN server_groups g ON g.id = gm.group_id
                JOIN servers s ON s.id = gm.server_id
                ORDER BY g.name, s.name;
                """
            )
            return cur.fetchall()


def list_enabled_servers() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, host, ssh_port, ssh_user, web_url, console_3xui_url, subscription_3xui_url, has_3xui, has_ssl_monitoring, has_http_monitoring
                FROM servers
                WHERE is_enabled = TRUE
                ORDER BY id;
                """
            )
            return cur.fetchall()



def _status_summary_json(**payload: Any) -> Jsonb:
    return Jsonb(payload)


def update_ping_status(server_id: int, ping_ok: bool | None, ping_latency_ms: int | None, error: str | None):
    summary_json = _status_summary_json(
        ping_ok=ping_ok,
        ping_latency_ms=ping_latency_ms,
        last_error=error,
        last_probe="ping",
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (server_id, ping_ok, ping_latency_ms, last_error, last_check_at, updated_at, summary_json)
                VALUES (%s, %s, %s, %s, NOW(), NOW(), %s)
                ON CONFLICT (server_id)
                DO UPDATE SET
                    ping_ok = EXCLUDED.ping_ok,
                    ping_latency_ms = EXCLUDED.ping_latency_ms,
                    last_error = EXCLUDED.last_error,
                    last_check_at = EXCLUDED.last_check_at,
                    updated_at = NOW(),
                    summary_json = server_status.summary_json || EXCLUDED.summary_json;
                """,
                (server_id, ping_ok, ping_latency_ms, error, summary_json),
            )
        conn.commit()


def update_ssh_status(server_id: int, ssh_ok: bool | None, ssh_latency_ms: int | None, error: str | None):
    summary_json = _status_summary_json(
        ssh_ok=ssh_ok,
        ssh_latency_ms=ssh_latency_ms,
        last_error=error,
        last_probe="ssh",
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (server_id, ssh_ok, ssh_latency_ms, last_error, last_check_at, updated_at, summary_json)
                VALUES (%s, %s, %s, %s, NOW(), NOW(), %s)
                ON CONFLICT (server_id)
                DO UPDATE SET
                    ssh_ok = EXCLUDED.ssh_ok,
                    ssh_latency_ms = EXCLUDED.ssh_latency_ms,
                    last_error = EXCLUDED.last_error,
                    last_check_at = EXCLUDED.last_check_at,
                    updated_at = NOW(),
                    summary_json = server_status.summary_json || EXCLUDED.summary_json;
                """,
                (server_id, ssh_ok, ssh_latency_ms, error, summary_json),
            )
        conn.commit()


def update_http_status(
    server_id: int,
    ok: bool | None = None,
    response_ms: int | None = None,
    status_code: int | None = None,
    error: str | None = None,
    checked_at = None,
    http_ok: bool | None = None,
    http_response_ms: int | None = None,
    http_status_code: int | None = None,
):
    if http_ok is not None or ok is None:
        ok = http_ok if http_ok is not None else ok
    if http_response_ms is not None or response_ms is None:
        response_ms = http_response_ms if http_response_ms is not None else response_ms
    if http_status_code is not None or status_code is None:
        status_code = http_status_code if http_status_code is not None else status_code

    summary_json = _status_summary_json(
        http_ok=ok,
        http_status_code=status_code,
        http_response_ms=response_ms,
        last_error=error,
        last_probe="http",
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (server_id, http_ok, http_status_code, http_response_ms, last_error, last_check_at, updated_at, summary_json)
                VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()), NOW(), %s)
                ON CONFLICT (server_id)
                DO UPDATE SET
                    http_ok = EXCLUDED.http_ok,
                    http_status_code = EXCLUDED.http_status_code,
                    http_response_ms = EXCLUDED.http_response_ms,
                    last_error = EXCLUDED.last_error,
                    last_check_at = EXCLUDED.last_check_at,
                    updated_at = NOW(),
                    summary_json = server_status.summary_json || EXCLUDED.summary_json;
                """,
                (server_id, ok, status_code, response_ms, error, checked_at, summary_json),
            )
        conn.commit()


def update_3xui_status(
    server_id: int,
    *,
    console_ok: bool | None,
    console_response_ms: int | None,
    console_status_code: int | None,
    console_error: str | None,
    console_checked_at = None,
    subscription_ok: bool | None,
    subscription_response_ms: int | None,
    subscription_status_code: int | None,
    subscription_error: str | None,
    subscription_checked_at = None,
):
    last_error = console_error or subscription_error
    summary_json = _status_summary_json(
        last_error=last_error,
        last_probe="xui",
        console_3xui_ok=console_ok,
        console_3xui_http_status=console_status_code,
        console_3xui_response_ms=console_response_ms,
        subscription_3xui_ok=subscription_ok,
        subscription_3xui_http_status=subscription_status_code,
        subscription_3xui_response_ms=subscription_response_ms,
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (
                    server_id,
                    console_3xui_ok,
                    console_3xui_http_status,
                    console_3xui_response_ms,
                    subscription_3xui_ok,
                    subscription_3xui_http_status,
                    subscription_3xui_response_ms,
                    last_error,
                    last_check_at,
                    updated_at,
                    summary_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, %s, NOW()), NOW(), %s)
                ON CONFLICT (server_id)
                DO UPDATE SET
                    console_3xui_ok = EXCLUDED.console_3xui_ok,
                    console_3xui_http_status = EXCLUDED.console_3xui_http_status,
                    console_3xui_response_ms = EXCLUDED.console_3xui_response_ms,
                    subscription_3xui_ok = EXCLUDED.subscription_3xui_ok,
                    subscription_3xui_http_status = EXCLUDED.subscription_3xui_http_status,
                    subscription_3xui_response_ms = EXCLUDED.subscription_3xui_response_ms,
                    last_error = COALESCE(EXCLUDED.last_error, server_status.last_error),
                    last_check_at = EXCLUDED.last_check_at,
                    updated_at = NOW(),
                    summary_json = server_status.summary_json || EXCLUDED.summary_json;
                """,
                (
                    server_id,
                    console_ok,
                    console_status_code,
                    console_response_ms,
                    subscription_ok,
                    subscription_status_code,
                    subscription_response_ms,
                    last_error,
                    console_checked_at,
                    subscription_checked_at,
                    summary_json,
                ),
            )
        conn.commit()


def insert_probe_history(
    server_id: int,
    server_name_snapshot: str,
    server_host_snapshot: str,
    probe_type: str,
    source: str,
    ok: bool | None,
    latency_ms: int | None = None,
    status_code: int | None = None,
    error: str | None = None,
    started_at = None,
    finished_at = None,
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO probe_history (
                    server_id,
                    server_name_snapshot,
                    server_host_snapshot,
                    probe_type,
                    source,
                    ok,
                    latency_ms,
                    status_code,
                    error,
                    started_at,
                    finished_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), COALESCE(%s, NOW()))
                RETURNING *;
                """,
                (
                    server_id,
                    server_name_snapshot,
                    server_host_snapshot,
                    probe_type,
                    source,
                    ok,
                    latency_ms,
                    status_code,
                    error,
                    started_at,
                    finished_at,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def list_probe_history(limit: int = 50, server_id: int | None = None, probe_type: str | None = None, source: str | None = None) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or 50), 500))
    clauses = []
    params: list[Any] = []
    if server_id is not None:
        clauses.append("ph.server_id = %s")
        params.append(server_id)
    if probe_type:
        clauses.append("ph.probe_type = %s")
        params.append(probe_type)
    if source:
        clauses.append("ph.source = %s")
        params.append(source)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            ph.id,
            ph.server_id,
            ph.server_name_snapshot AS server_name,
            ph.server_host_snapshot AS server_host,
            ph.probe_type,
            ph.source,
            ph.ok,
            ph.latency_ms,
            ph.status_code,
            ph.error,
            ph.started_at,
            ph.finished_at,
            ph.created_at
        FROM probe_history ph
        {where_sql}
        ORDER BY ph.started_at DESC, ph.id DESC
        LIMIT %s;
    """
    params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def get_monitor_settings() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    scheduler_enabled,
                    ping_interval_seconds,
                    ssh_interval_seconds,
                    http_interval_seconds,
                    xui_interval_seconds,
                    ssl_interval_seconds,
                    ping_timeout_seconds,
                    tcp_timeout_seconds,
                    http_timeout_seconds,
                    xui_timeout_seconds,
                    ssl_timeout_seconds,
                    last_ping_scheduler_run_at,
                    last_ssh_scheduler_run_at,
                    last_http_scheduler_run_at,
                    last_xui_scheduler_run_at,
                    last_ssl_scheduler_run_at
                FROM monitor_settings
                WHERE id = 1;
                """
            )
            row = cur.fetchone()
        conn.commit()
        return row or {
            "scheduler_enabled": False,
            "ping_interval_seconds": 60,
            "ssh_interval_seconds": 60,
            "http_interval_seconds": 120,
            "xui_interval_seconds": 240,
            "ssl_interval_seconds": 300,
            "ping_timeout_seconds": 2,
            "tcp_timeout_seconds": 3,
            "http_timeout_seconds": 5,
            "xui_timeout_seconds": 5,
            "ssl_timeout_seconds": 5,
            "last_ping_scheduler_run_at": None,
            "last_ssh_scheduler_run_at": None,
            "last_http_scheduler_run_at": None,
            "last_xui_scheduler_run_at": None,
            "last_ssl_scheduler_run_at": None,
        }


def update_monitor_settings(
    scheduler_enabled: bool,
    ping_interval_seconds: int,
    ssh_interval_seconds: int,
    http_interval_seconds: int,
    xui_interval_seconds: int,
    ssl_interval_seconds: int,
    ping_timeout_seconds: int,
    tcp_timeout_seconds: int,
    http_timeout_seconds: int,
    xui_timeout_seconds: int,
    ssl_timeout_seconds: int,
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE monitor_settings
                SET scheduler_enabled = %s,
                    ping_interval_seconds = %s,
                    ssh_interval_seconds = %s,
                    http_interval_seconds = %s,
                    xui_interval_seconds = %s,
                    ssl_interval_seconds = %s,
                    ping_timeout_seconds = %s,
                    tcp_timeout_seconds = %s,
                    http_timeout_seconds = %s,
                    xui_timeout_seconds = %s,
                    ssl_timeout_seconds = %s,
                    updated_at = NOW()
                WHERE id = 1
                RETURNING *;
                """,
                (
                    scheduler_enabled,
                    ping_interval_seconds,
                    ssh_interval_seconds,
                    http_interval_seconds,
                    xui_interval_seconds,
                    ssl_interval_seconds,
                    ping_timeout_seconds,
                    tcp_timeout_seconds,
                    http_timeout_seconds,
                    xui_timeout_seconds,
                    ssl_timeout_seconds,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def mark_scheduler_probe_run(probe_type: str) -> dict[str, Any]:
    probe_type = (probe_type or '').strip().lower()
    column_map = {
        'ping': 'last_ping_scheduler_run_at',
        'ssh': 'last_ssh_scheduler_run_at',
        'http': 'last_http_scheduler_run_at',
        'xui': 'last_xui_scheduler_run_at',
        'ssl': 'last_ssl_scheduler_run_at',
    }
    column = column_map.get(probe_type)
    if not column:
        raise ValueError('Unsupported probe type for scheduler state update')

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE monitor_settings SET {column} = NOW(), updated_at = NOW() WHERE id = 1 RETURNING *;"
            )
            row = cur.fetchone()
        conn.commit()
        return row


def update_ssl_status(
    server_id: int,
    ok: bool | None,
    error: str | None,
    payload: dict[str, Any] | None = None,
    source: str | None = None,
):
    payload = dict(payload or {})
    if source and "source" not in payload:
        payload["source"] = source

    summary_json = _status_summary_json(
        ssl_ok=ok,
        ssl_error=error,
        ssl_last_probe=payload,
        last_error=error,
        last_probe="ssl",
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (server_id, ssl_ok, last_error, last_check_at, updated_at, summary_json)
                VALUES (%s, %s, %s, NOW(), NOW(), %s)
                ON CONFLICT (server_id) DO UPDATE SET
                    ssl_ok = EXCLUDED.ssl_ok,
                    last_error = CASE
                        WHEN EXCLUDED.last_error IS NOT NULL AND EXCLUDED.last_error <> '' THEN EXCLUDED.last_error
                        ELSE server_status.last_error
                    END,
                    last_check_at = NOW(),
                    updated_at = NOW(),
                    summary_json = COALESCE(server_status.summary_json, '{}'::jsonb) || EXCLUDED.summary_json;
                """,
                (server_id, ok, error, summary_json),
            )
        conn.commit()


def set_alert_active(server_id: int, alert_type: str, severity: str, message: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM alerts WHERE server_id = %s AND alert_type = %s AND status = 'active' ORDER BY id DESC LIMIT 1;", (server_id, alert_type))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE alerts SET severity = %s, message = %s, last_seen_at = NOW(), updated_at = NOW() WHERE id = %s RETURNING *;", (severity, message, row['id']))
                result = cur.fetchone()
                result['_event'] = 'updated'
            else:
                cur.execute(
                    """
                    INSERT INTO alerts (server_id, alert_type, severity, status, message, first_seen_at, last_seen_at, created_at, updated_at)
                    VALUES (%s, %s, %s, 'active', %s, NOW(), NOW(), NOW(), NOW())
                    RETURNING *;
                    """,
                    (server_id, alert_type, severity, message),
                )
                result = cur.fetchone()
                result['_event'] = 'created'
        conn.commit()
        return result


def resolve_alert(server_id: int, alert_type: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE alerts SET status = 'resolved', resolved_at = NOW(), last_seen_at = NOW(), updated_at = NOW() WHERE server_id = %s AND alert_type = %s AND status = 'active' RETURNING *;",
                (server_id, alert_type),
            )
            rows = cur.fetchall()
        conn.commit()
        return rows


def list_active_alerts() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.server_id,
                    s.name AS server_name,
                    s.host AS server_host,
                    a.alert_type,
                    a.severity,
                    a.status,
                    a.message,
                    a.notify_count,
                    a.last_notified_at,
                    a.last_delivery_status,
                    a.last_delivery_error,
                    a.first_seen_at,
                    a.last_seen_at,
                    a.resolved_at,
                    a.updated_at
                FROM alerts a
                LEFT JOIN servers s ON s.id = a.server_id
                WHERE a.status = 'active'
                ORDER BY a.last_seen_at DESC, a.id DESC;
                """
            )
            return cur.fetchall()


def get_alert_settings() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    notifications_enabled,
                    notify_on_new_alert,
                    notify_on_resolved,
                    stale_alert_enabled,
                    stale_after_seconds,
                    reminder_interval_seconds,
                    created_at,
                    updated_at
                FROM alert_settings
                WHERE id = 1;
                """
            )
            row = cur.fetchone()
            if row:
                return row
        conn.commit()
    init_db()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM alert_settings WHERE id = 1;")
            return cur.fetchone()


def update_alert_settings(
    notifications_enabled: bool,
    notify_on_new_alert: bool,
    notify_on_resolved: bool,
    stale_alert_enabled: bool,
    stale_after_seconds: int,
    reminder_interval_seconds: int,
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alert_settings
                SET
                    notifications_enabled = %s,
                    notify_on_new_alert = %s,
                    notify_on_resolved = %s,
                    stale_alert_enabled = %s,
                    stale_after_seconds = %s,
                    reminder_interval_seconds = %s,
                    updated_at = NOW()
                WHERE id = 1
                RETURNING *;
                """,
                (
                    notifications_enabled,
                    notify_on_new_alert,
                    notify_on_resolved,
                    stale_alert_enabled,
                    stale_after_seconds,
                    reminder_interval_seconds,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def insert_alert_delivery_log(
    alert_id: int | None,
    server_id: int | None,
    server_name_snapshot: str | None,
    server_host_snapshot: str | None,
    alert_type: str | None,
    event_type: str,
    channel: str,
    target: str | None,
    status: str,
    message: str | None,
    error: str | None,
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_delivery_log (
                    alert_id,
                    server_id,
                    server_name_snapshot,
                    server_host_snapshot,
                    alert_type,
                    event_type,
                    channel,
                    target,
                    status,
                    message,
                    error
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (
                    alert_id,
                    server_id,
                    server_name_snapshot,
                    server_host_snapshot,
                    alert_type,
                    event_type,
                    channel,
                    target,
                    status,
                    message,
                    error,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def list_alert_delivery_log(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or 50), 500))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    alert_id,
                    server_id,
                    server_name_snapshot,
                    server_host_snapshot,
                    alert_type,
                    event_type,
                    channel,
                    target,
                    status,
                    message,
                    error,
                    created_at
                FROM alert_delivery_log
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cur.fetchall()


def mark_alert_delivery_attempt(alert_id: int, status: str, error: str | None = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alerts
                SET
                    notify_count = COALESCE(notify_count, 0) + 1,
                    last_notified_at = NOW(),
                    last_delivery_status = %s,
                    last_delivery_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *;
                """,
                (status, error, alert_id),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def list_servers_requiring_stale_alert(stale_after_seconds: int) -> list[dict[str, Any]]:
    stale_after_seconds = max(60, int(stale_after_seconds or 60))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    s.host,
                    st.last_check_at,
                    st.last_error,
                    EXTRACT(EPOCH FROM (NOW() - st.last_check_at))::BIGINT AS stale_for_seconds
                FROM servers s
                JOIN server_status st ON st.server_id = s.id
                WHERE
                    s.is_enabled = TRUE
                    AND st.last_check_at IS NOT NULL
                    AND st.last_check_at < NOW() - (%s * INTERVAL '1 second')
                ORDER BY st.last_check_at ASC, s.id ASC;
                """,
                (stale_after_seconds,),
            )
            return cur.fetchall()


def list_alerts_for_reminder(reminder_interval_seconds: int) -> list[dict[str, Any]]:
    reminder_interval_seconds = max(60, int(reminder_interval_seconds or 60))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.*,
                    s.name AS server_name,
                    s.host AS server_host
                FROM alerts a
                LEFT JOIN servers s ON s.id = a.server_id
                WHERE
                    a.status = 'active'
                    AND a.last_notified_at IS NOT NULL
                    AND a.last_notified_at < NOW() - (%s * INTERVAL '1 second')
                ORDER BY a.last_seen_at ASC, a.id ASC;
                """,
                (reminder_interval_seconds,),
            )
            return cur.fetchall()


def get_summary() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            q = lambda sql: (cur.execute(sql), cur.fetchone()["count"])[1]
            servers_total = q("SELECT COUNT(*)::INTEGER AS count FROM servers;")
            servers_enabled = q("SELECT COUNT(*)::INTEGER AS count FROM servers WHERE is_enabled = TRUE;")
            groups_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_groups;")
            group_links_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_group_members;")
            ping_ok_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS TRUE;")
            ping_fail_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS FALSE;")
            ping_unknown_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS NULL;")
            ssh_ok_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ssh_ok IS TRUE;")
            ssh_fail_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ssh_ok IS FALSE;")
            ssh_unknown_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ssh_ok IS NULL;")
            http_ok_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE http_ok IS TRUE;")
            http_fail_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE http_ok IS FALSE;")
            http_unknown_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE http_ok IS NULL;")
            xui_ok_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE subscription_3xui_ok IS TRUE OR console_3xui_ok IS TRUE;")
            xui_fail_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE subscription_3xui_ok IS FALSE OR console_3xui_ok IS FALSE;")
            ssl_ok_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ssl_ok IS TRUE;")
            ssl_fail_total = q("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ssl_ok IS FALSE;")
            active_alerts_total = q("SELECT COUNT(*)::INTEGER AS count FROM alerts WHERE status = 'active';")
            cur.execute(
                """
                SELECT
                    scheduler_enabled,
                    last_ping_scheduler_run_at,
                    last_ssh_scheduler_run_at,
                    last_http_scheduler_run_at,
                    last_xui_scheduler_run_at,
                    last_ssl_scheduler_run_at
                FROM monitor_settings
                WHERE id = 1;
                """
            )
            monitor = cur.fetchone() or {}

        return {
            "servers_total": servers_total,
            "servers_enabled": servers_enabled,
            "groups_total": groups_total,
            "group_links_total": group_links_total,
            "ping_ok_total": ping_ok_total,
            "ping_fail_total": ping_fail_total,
            "ping_unknown_total": ping_unknown_total,
            "ssh_ok_total": ssh_ok_total,
            "ssh_fail_total": ssh_fail_total,
            "ssh_unknown_total": ssh_unknown_total,
            "http_ok_total": http_ok_total,
            "http_fail_total": http_fail_total,
            "http_unknown_total": http_unknown_total,
            "xui_ok_total": xui_ok_total,
            "xui_fail_total": xui_fail_total,
            "ssl_ok_total": ssl_ok_total,
            "ssl_fail_total": ssl_fail_total,
            "active_alerts_total": active_alerts_total,
            "scheduler_enabled": monitor.get("scheduler_enabled"),
            "last_ping_scheduler_run_at": monitor.get("last_ping_scheduler_run_at"),
            "last_ssh_scheduler_run_at": monitor.get("last_ssh_scheduler_run_at"),
            "last_http_scheduler_run_at": monitor.get("last_http_scheduler_run_at"),
            "last_xui_scheduler_run_at": monitor.get("last_xui_scheduler_run_at"),
            "last_ssl_scheduler_run_at": monitor.get("last_ssl_scheduler_run_at"),
        }
