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
- `0.1.14` — интерфейс стал пригоден для работы, форма в тёмной теме исправлена.

Текущий релиз в работе:
- `0.1.15`
- добавлены проверки доступности SSH-порта и HTTP/HTTPS;
- в inventory сервера добавлены `web_url` и `has_http_monitoring`;
- alerts теперь могут подниматься по `ping_down`, `ssh_down`, `http_down`;
- следующим функциональным блоком остаются 3x-ui checks, затем SSL и Ansible execution layer.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
