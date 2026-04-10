# Перенос проекта в новый чат

Проект: ServerOrchestration
Репозиторий: https://github.com/messireL/ServerOrchestration
Текущий режим работы:
- GitHub — основной источник кода
- Portainer — основной deploy/update
- Docker Compose — обязательный формат stack
- Non-root контейнеры приложения — обязательны
- Прямой docker compose на сервере — fallback/диагностика

Ключевые требования:
- inventory серверов и групп
- отдельная таблица состояния проверок
- ping и probe-проверки вне Ansible
- Ansible для серверных действий
- alerting (email / Telegram)
- проверка 3x-ui console/subscription
- проверка SSL, timezone, apt, reboot, журналы UFW/SSH
- обязательная версионность релизов и папка `docs/releases/<версия>/`

Текущий подтверждённый рабочий релиз до этого шага:
- `0.1.3` — GitHub + Portainer deploy подтверждён, backend/DB/version/summary работают.

Текущий релиз в работе:
- `0.1.4`
- добавлен read-only web dashboard `/`
- добавлены `alerts`
- добавлен ручной `ping probe` через API и web-интерфейс
- результаты ping сохраняются в `server_status`

Важные правила:
- timezone по умолчанию: `Europe/Moscow`
- в Portainer не нужно задавать `APP_VERSION`
- серверы в рабочем контуре будем заводить позже через отдельный web-интерфейс inventory, не через curl
