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
- `0.1.17` — ping probe больше не падает `Internal Server Error`, schema-sync legacy-колонок добавлен.

Текущий релиз в работе:
- `0.1.18`
- hotfix после `0.1.17`, потому что ping после запуска не показывал latency/time в таблицах;
- релиз усиливает парсинг вывода `ping` и добавляет fallback на measured elapsed time, если стандартная строка latency не распознана;
- таблицы Dashboard/Проверки теперь должны явно показывать `N ms`, а не пустое значение при успешном ping;
- после подтверждения следующими шагами идут переработка интерфейса, inventory polish, scheduler проверок, затем 3x-ui и SSL.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
