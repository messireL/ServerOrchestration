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
- `0.1.4` — GitHub + Portainer deploy работает, summary/status/alerts/ping foundation подтверждены.

Текущий релиз в работе:
- `0.1.5`
- добавлен более живой web UI
- добавлены web-формы для добавления групп
- добавлены web-формы для добавления серверов
- добавлена привязка серверов к группам через интерфейс
- сохранён ручной запуск `ping probe` из UI

Важные правила:
- timezone по умолчанию: `Europe/Moscow`
- в Portainer не нужно задавать `APP_VERSION`
- серверы начинаем заводить уже через web-интерфейс, а не через curl
