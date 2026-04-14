# Проверка релиза v0.1.26

1. Открыть `Проверки` и выполнить ручной запуск connectivity/http probes.
2. Проверить backend logs: нет `NameError: _execute_xui_batch is not defined`.
3. Открыть `/api/probes/history` и убедиться, что после очередного интервала появились записи `probe_type=xui`, `source=scheduler`.
4. Открыть `/api/status/servers` и убедиться, что поля `console_3xui_*` / `subscription_3xui_*` продолжают обновляться.
5. Проверить `/health` и `/version`.
