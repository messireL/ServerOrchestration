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
- `0.1.16` — inventory/connectivity hotfix: форма сервера восстановлена, `Web URL` и `Проверять HTTP/HTTPS` снова видны, кнопка `Добавить сервер` работает.

Текущий релиз в работе:
- `0.1.17`
- hotfix после `0.1.16`, потому что запуск ping-проверки мог падать `Internal Server Error`;
- релиз добавляет schema-sync legacy-колонок `servers` и `server_status`, включая `server_status.summary_json`;
- probe-endpoints должны возвращать результат по серверам без падения всего API 500-кой;
- после подтверждения следующими шагами идут переработка интерфейса, inventory polish, scheduler проверок, затем 3x-ui и SSL.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
