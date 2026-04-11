# Tests 0.1.19

- `/version` возвращает `0.1.19`;
- `/api/probes/ping/diagnostics` возвращает JSON и показывает `binary_found=true`;
- `self_test.ok` в diagnostics должен быть `true`;
- ручной запуск ping probe из UI больше не даёт `failed=1` по причине отсутствия прав на ICMP;
- в таблице Проверки после успешного ping виден `ping: N ms`;
- если ping всё же падает, UI показывает warning с первой причиной ошибки.
