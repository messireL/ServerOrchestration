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
- `0.1.20`
- hotfix записи результатов probe-проверок в PostgreSQL;
- исправлена передача `summary_json` в `server_status` через typed `jsonb`, чтобы PostgreSQL не падал на `could not determine data type of parameter $7` при `NULL`;
- фикс затрагивает `ping`, `SSH` и `HTTP`, чтобы та же мина не рванула позже в соседнем endpoint;
- диагностика ping и `NET_RAW` из `0.1.19` сохранены;
- пояснение по Portainer оставлено: новые task/container имена при redeploy — нормальная механика, а старые stopped-экземпляры надо периодически чистить prune.

Ближайший следующий шаг после подтверждения:
- `0.1.21` — переработка интерфейса и экранов с нормальным левым меню и чистой структурой разделов.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
