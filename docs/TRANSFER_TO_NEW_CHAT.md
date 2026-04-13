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
- scheduler мониторинга с хранением настроек в БД;
- история ручных и фоновых прогонов;
- Ansible для серверных действий и изменений;
- alerting (email / Telegram);
- проверка 3x-ui console/subscription;
- проверка SSL, timezone, apt, reboot, журналы UFW/SSH;
- обязательная версионность релизов и папка `docs/releases/<версия>/`.

Текущий подтверждённый рабочий релиз:
- `0.1.23` — scheduler и история проверок работают, приоритет смещён на функциональные релизы.

Текущий релиз в работе:
- `0.1.24`
- добавлены настройки alerting, stale-monitoring и журнал доставок;
- реализованы Telegram/email уведомления через env-конфиг Portainer;
- active alerts теперь хранят счётчик уведомлений и последний статус доставки;
- UI-полировка не является приоритетом, дальше идём в функциональные релизы мониторинга.

Ближайший следующий шаг после подтверждения:
- `0.1.25` — 3x-ui console/subscription checks;
- `0.1.26` — SSL checks;
- `0.1.27` — ansible groundwork / operational actions;
- далее operational-контур и безопасный service-user workflow.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
