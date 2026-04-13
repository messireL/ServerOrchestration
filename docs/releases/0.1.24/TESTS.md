# Tests for 0.1.24

- `/version` возвращает `0.1.24`;
- `/api/alerts/settings` читает и сохраняет настройки;
- `/api/alerts/test` создаёт запись в delivery log;
- при падении ping/ssh/http создаётся active alert и меняется `notify_count`;
- stale-monitoring создаёт `monitor_stale`, если `last_check_at` устарел;
- `/api/alerts/deliveries` показывает sent/failed/skipped без чтения docker logs.
