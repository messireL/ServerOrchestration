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

Правило релизов:
- каждый релиз имеет свою версию
- в каждом релизе ведутся изменения и баги в `docs/releases/<версия>/`
- версия хранится в файле `VERSION`
- для Portainer не требуется вручную задавать `APP_VERSION`
