# Tests for 0.1.20

После выкладки проверить:
- `/version` возвращает `0.1.20`;
- `/api/probes/ping/diagnostics` возвращает JSON;
- `POST /api/probes/ping/run` больше не отдаёт `db persistence failed`;
- `GET /api/status/servers` показывает `ping_ok` / `ping_latency_ms`;
- в UI в разделе Проверки ping перестаёт зависать в `unknown`, а при доступности хоста показывает latency.
