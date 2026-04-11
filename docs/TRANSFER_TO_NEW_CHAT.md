# Перенос проекта в новый чат

Проект: Система мониторинга
Репозиторий: https://github.com/messireL/ServerOrchestration
Текущий режим работы:
- GitHub — основной источник кода
- Portainer — основной deploy/update
- Docker Compose — обязательный формат stack
- Non-root контейнеры приложения — обязательны
- Прямой docker compose на сервере — fallback/диагностика

Ключевые требования:
- inventory серверов и групп;
- отдельная таблица состояния проверок;
- ping, SSH и HTTP/HTTPS probe-проверки вне Ansible;
- Ansible для серверных действий и изменений;
- alerting (email / Telegram);
- проверка 3x-ui console/subscription;
- проверка SSL, timezone, apt, reboot, журналы UFW/SSH;
- обязательная версионность релизов и папка `docs/releases/<версия>/`.

Текущий подтверждённый рабочий релиз до этого шага:
- `0.1.18` — ping endpoint перестал валиться `500`, но сам ICMP ping на стенде ещё не выполнялся корректно.

Текущий релиз в работе:
- `0.1.19`
- hotfix реального выполнения ping в non-root контейнере;
- в backend image добавлен `setcap cap_net_raw=+ep` для системного `ping`;
- в compose для backend добавлен `cap_add: NET_RAW`;
- добавлен diagnostics endpoint `/api/probes/ping/diagnostics` и более честное warning-сообщение в UI с первой причиной провала ping;
- параллельно зафиксировано объяснение по Portainer: при stack/swarm redeploy контейнеры могут получать новые task-имена, а старые stopped-экземпляры нужно периодически чистить prune, иначе сервер начнёт коллекционировать цифровые трупы.

Ближайший следующий шаг после подтверждения:
- `0.1.20` — уже не очередной бой с ping, а нормальная переработка интерфейса и экранов.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
