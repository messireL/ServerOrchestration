import os
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row


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
                    description TEXT,
                    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    has_3xui BOOLEAN NOT NULL DEFAULT FALSE,
                    has_ssl_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE servers ALTER COLUMN ssh_user SET DEFAULT 'srvops';")

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
                    console_3xui_ok BOOLEAN,
                    subscription_3xui_ok BOOLEAN,
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
            cur.execute("ALTER TABLE server_status ADD COLUMN IF NOT EXISTS last_error TEXT;")

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
                    s.description,
                    s.is_enabled,
                    s.has_3xui,
                    s.has_ssl_monitoring,
                    s.created_at,
                    s.updated_at,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.console_3xui_ok,
                    st.subscription_3xui_ok,
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
                    st.console_3xui_ok,
                    st.subscription_3xui_ok,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at
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
                    s.is_enabled,
                    s.has_3xui,
                    s.has_ssl_monitoring,
                    st.ping_ok,
                    st.ping_latency_ms,
                    st.ssh_ok,
                    st.console_3xui_ok,
                    st.subscription_3xui_ok,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at,
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
                    st.console_3xui_ok,
                    st.subscription_3xui_ok,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_error,
                    st.last_check_at,
                    st.updated_at
                ORDER BY s.id;
                """
            )
            return cur.fetchall()


def create_server(
    name: str,
    host: str,
    ssh_port: int,
    ssh_user: str,
    description: str | None,
    is_enabled: bool,
    has_3xui: bool,
    has_ssl_monitoring: bool,
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO servers
                    (name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring),
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO server_status (server_id)
                VALUES (%s)
                ON CONFLICT (server_id) DO NOTHING;
                """,
                (row["id"],),
            )
        conn.commit()
        return row


def update_server(
    server_id: int,
    name: str,
    host: str,
    ssh_port: int,
    ssh_user: str,
    description: str | None,
    is_enabled: bool,
    has_3xui: bool,
    has_ssl_monitoring: bool,
):
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
                    description = %s,
                    is_enabled = %s,
                    has_3xui = %s,
                    has_ssl_monitoring = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *;
                """,
                (name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring, server_id),
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
            cur.execute(
                """
                INSERT INTO server_groups (name, description)
                VALUES (%s, %s)
                RETURNING *;
                """,
                (name, description),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def update_group(group_id: int, name: str, description: str | None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE server_groups
                SET name = %s, description = %s
                WHERE id = %s
                RETURNING *;
                """,
                (name, description, group_id),
            )
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
            cur.execute(
                """
                INSERT INTO server_group_members (group_id, server_id)
                VALUES (%s, %s)
                ON CONFLICT (group_id, server_id) DO NOTHING;
                """,
                (group_id, server_id),
            )
        conn.commit()
    return {"group_id": group_id, "server_id": server_id, "linked": True}


def detach_server_from_group(group_id: int, server_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM server_group_members WHERE group_id = %s AND server_id = %s RETURNING group_id, server_id;",
                (group_id, server_id),
            )
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
                SELECT id, name, host, ssh_port, ssh_user, has_3xui, has_ssl_monitoring
                FROM servers
                WHERE is_enabled = TRUE
                ORDER BY id;
                """
            )
            return cur.fetchall()


def update_ping_status(server_id: int, ping_ok: bool, ping_latency_ms: int | None, error: str | None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO server_status (
                    server_id,
                    ping_ok,
                    ping_latency_ms,
                    last_error,
                    last_check_at,
                    updated_at,
                    summary_json
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    NOW(),
                    jsonb_build_object(
                        'ping_ok', %s,
                        'ping_latency_ms', %s,
                        'last_error', %s,
                        'last_probe', 'ping'
                    )
                )
                ON CONFLICT (server_id)
                DO UPDATE SET
                    ping_ok = EXCLUDED.ping_ok,
                    ping_latency_ms = EXCLUDED.ping_latency_ms,
                    last_error = EXCLUDED.last_error,
                    last_check_at = EXCLUDED.last_check_at,
                    updated_at = NOW(),
                    summary_json = EXCLUDED.summary_json;
                """,
                (server_id, ping_ok, ping_latency_ms, error, ping_ok, ping_latency_ms, error),
            )
        conn.commit()


def set_alert_active(server_id: int, alert_type: str, severity: str, message: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM alerts
                WHERE server_id = %s AND alert_type = %s AND status = 'active'
                ORDER BY id DESC
                LIMIT 1;
                """,
                (server_id, alert_type),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE alerts
                    SET
                        severity = %s,
                        message = %s,
                        last_seen_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (severity, message, row["id"]),
                )
                result = cur.fetchone()
            else:
                cur.execute(
                    """
                    INSERT INTO alerts (
                        server_id,
                        alert_type,
                        severity,
                        status,
                        message,
                        first_seen_at,
                        last_seen_at,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, 'active', %s, NOW(), NOW(), NOW(), NOW())
                    RETURNING *;
                    """,
                    (server_id, alert_type, severity, message),
                )
                result = cur.fetchone()
        conn.commit()
        return result


def resolve_alert(server_id: int, alert_type: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alerts
                SET
                    status = 'resolved',
                    resolved_at = NOW(),
                    last_seen_at = NOW(),
                    updated_at = NOW()
                WHERE server_id = %s AND alert_type = %s AND status = 'active'
                RETURNING id;
                """,
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


def get_summary() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM servers;")
            servers_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM servers WHERE is_enabled = TRUE;")
            servers_enabled = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM server_groups;")
            groups_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM server_group_members;")
            group_links_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS TRUE;")
            ping_ok_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS FALSE;")
            ping_fail_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM server_status WHERE ping_ok IS NULL;")
            ping_unknown_total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*)::INTEGER AS count FROM alerts WHERE status = 'active';")
            active_alerts_total = cur.fetchone()["count"]

        return {
            "servers_total": servers_total,
            "servers_enabled": servers_enabled,
            "groups_total": groups_total,
            "group_links_total": group_links_total,
            "ping_ok_total": ping_ok_total,
            "ping_fail_total": ping_fail_total,
            "ping_unknown_total": ping_unknown_total,
            "active_alerts_total": active_alerts_total,
        }
