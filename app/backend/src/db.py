import os
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS server_groups (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    host TEXT NOT NULL,
                    ssh_port INTEGER NOT NULL DEFAULT 22,
                    ssh_user TEXT NOT NULL DEFAULT 'root',
                    description TEXT,
                    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    has_3xui BOOLEAN NOT NULL DEFAULT FALSE,
                    has_ssl_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS server_group_members (
                    group_id BIGINT NOT NULL REFERENCES server_groups(id) ON DELETE CASCADE,
                    server_id BIGINT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (group_id, server_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS server_status (
                    server_id BIGINT PRIMARY KEY REFERENCES servers(id) ON DELETE CASCADE,
                    ping_ok BOOLEAN,
                    ssh_ok BOOLEAN,
                    console_3xui_ok BOOLEAN,
                    subscription_3xui_ok BOOLEAN,
                    ssl_ok BOOLEAN,
                    reboot_required BOOLEAN,
                    last_check_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );
            """)

        conn.commit()

def list_servers():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
                    st.ssh_ok,
                    st.console_3xui_ok,
                    st.subscription_3xui_ok,
                    st.ssl_ok,
                    st.reboot_required,
                    st.last_check_at,
                    st.updated_at AS status_updated_at
                FROM servers s
                LEFT JOIN server_status st ON st.server_id = s.id
                ORDER BY s.id;
            """)
            return cur.fetchall()

def create_server(name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO servers
                    (name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (name, host, ssh_port, ssh_user, description, is_enabled, has_3xui, has_ssl_monitoring))
            row = cur.fetchone()

            cur.execute("""
                INSERT INTO server_status (server_id)
                VALUES (%s)
                ON CONFLICT (server_id) DO NOTHING;
            """, (row["id"],))

        conn.commit()
        return row

def list_groups():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
            """)
            return cur.fetchall()

def create_group(name, description):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO server_groups (name, description)
                VALUES (%s, %s)
                RETURNING *;
            """, (name, description))
            row = cur.fetchone()
        conn.commit()
        return row

def attach_server_to_group(group_id, server_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO server_group_members (group_id, server_id)
                VALUES (%s, %s)
                ON CONFLICT (group_id, server_id) DO NOTHING;
            """, (group_id, server_id))
        conn.commit()
    return {"group_id": group_id, "server_id": server_id, "linked": True}

def get_summary():
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

        return {
            "servers_total": servers_total,
            "servers_enabled": servers_enabled,
            "groups_total": groups_total,
            "group_links_total": group_links_total,
        }
