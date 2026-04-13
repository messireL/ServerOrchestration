# Регламент релизов

Каждый релиз обязан иметь:
- уникальную версию;
- архив релиза;
- папку `docs/releases/<версия>/`;
- описание изменений;
- список известных багов;
- порядок проверки;
- результат deploy/update.

Если используется GitHub:
- в ответе по релизу обязательно даётся commit message;
- основной deploy/update делается через Portainer Stack из Git-репозитория.

Если используется Docker:
- в релизе обязательно описывается, какой compose-файл использовать;
- описываются шаги проверки контейнеров, health endpoint и логов.

## Дополнение v0.1.24
- Для функциональных релизов мониторинга обязательно обновляются `README.md`, `docs/TZ.md`, `docs/ARCHITECTURE.md`, `docs/TRANSFER_TO_NEW_CHAT.md` и `docs/releases/<version>/*`.
- Если меняется scheduler или история прогонов, релиз обязан проверять сценарий старой БД без ручных SQL-правок.
- Для release мониторинга обязательно проверять `/health`, `/version`, `/api/summary`, `/api/status/servers`, `/api/monitor/settings`, `/api/probes/history` и профильные probe-endpoints.
- Если релиз включает background scheduler, нужно отдельно проверять, что после старта backend появляются автоматические записи history без ручного запуска из UI.
- Для Portainer workflow нельзя создавать новый stack на каждый релиз; обновляется существующий stack, а старые stopped-контейнеры и dangling images периодически чистятся отдельно.

- Если релиз меняет alerting, нужно отдельно проверять `/api/alerts`, `/api/alerts/settings`, `/api/alerts/deliveries` и `/api/alerts/test`.
- Для notification-каналов секреты не кладутся в UI или git: они задаются через Portainer env.
