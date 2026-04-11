# Tests 0.1.17

Проверить:
- `/health`;
- `/version` возвращает `0.1.17`;
- `POST /api/probes/ping/run` больше не даёт `Internal Server Error`;
- при недоступном хосте ping probe возвращает `failed`, а не 500;
- `/api/probes/ssh/run` и `/api/probes/http/run` тоже не валят весь endpoint при ошибке записи статуса;
- `/api/status/servers` показывает обновлённые значения после запуска проверок.
