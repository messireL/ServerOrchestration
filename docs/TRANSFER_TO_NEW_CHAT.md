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

Текущий подтверждённый рабочий релиз:
- `0.1.21` — probe-контур стабилизирован, ping на стенде проходит.

Текущий релиз в работе:
- `0.1.22`
- UI-полировка inventory и мониторинга без изменения backend API;
- sidebar разбит на рабочие секции;
- добавлена оперативная сводка в sidebar;
- на экране серверов появились быстрые фильтры: все / включённые / с проблемами / с alerts / с HTTP-monitoring;
- статусы ping/SSH/HTTP на inventory-экране отображаются отдельными бейджами;
- в списке серверов появился короткий хвост `last_error` рядом с `last_check`;
- на экране проверок добавлена summary-панель по результатам probe;
- roadmap в UI выровнен по версиям.

Ближайший следующий шаг после подтверждения:
- `0.1.23` — scheduler и история проверок;
- `0.1.24` — 3x-ui console/subscription checks;
- `0.1.25` — SSL checks;
- далее operational-контур через Ansible.

Важные правила:
- timezone по умолчанию: `Europe/Moscow`;
- в Portainer не нужно задавать `APP_VERSION`;
- внешний адрес панели задаётся через `APP_PUBLIC_BASE_URL`;
- root для SSH не нужен; позже использовать отдельного service-user, когда дойдём до Ansible/операционных действий.
