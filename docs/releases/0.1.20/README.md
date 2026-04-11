# Release 0.1.20

## Что сделано
- исправлена запись результатов probe-проверок в `server_status.summary_json`;
- `summary_json` теперь передаётся в PostgreSQL как typed `jsonb`, а не собирается через `jsonb_build_object` с неявно типизированными `NULL`;
- hotfix покрывает `ping`, `SSH` и `HTTP` persistence;
- сохранены изменения `0.1.19` по `NET_RAW`, `setcap` и `/api/probes/ping/diagnostics`;
- обновлены документация и пакет переноса в новый чат.

## Причина релиза
На стенде ping уже выполнялся, но запись результата падала с ошибкой вида `db persistence failed: could not determine data type of parameter $7`. Из-за этого UI показывал `failed=1`, а статусы оставались `unknown`.
