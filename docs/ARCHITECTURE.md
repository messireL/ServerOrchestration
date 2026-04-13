# Архитектура проекта

## Актуальное решение
- GitHub — основной источник кода проекта.
- Portainer — основной путь deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback и диагностика.
- Контейнеры приложения должны быть non-root.
- PostgreSQL хранит inventory, состояние проверок, alerts, настройки scheduler и историю прогонов.
- Быстрые проверки (`ping`, `SSH`, `HTTP/HTTPS`, затем 3x-ui console/subscription) идут отдельным probe-слоем, не через Ansible.
- Ansible используется как исполнительный слой для операций изменения: apt, timezone, reboot, 3x-ui update/restart, сбор журналов и т.п.

## Актуальное уточнение v0.1.24
- inventory сервера хранит `web_url` и флаг `has_http_monitoring`;
- probe-слой умеет:
  - ICMP ping;
  - TCP connect к SSH-порту;
  - HTTP/HTTPS запрос к `web_url` с browser-like headers;
- результаты probe-проверок пишутся в `server_status`;
- scheduler-настройки хранятся в таблице `monitor_settings`;
- история ручных и фоновых прогонов хранится в таблице `probe_history`;
- background scheduler поднимается вместе с backend и сам запускает due-проверки;
- последние scheduler-run по ping / SSH / HTTP хранятся в БД, а не только в памяти процесса;
- endpoint `/api/probes/ping/diagnostics` остаётся обязательным быстрым средством диагностики контейнера;
- экран `Проверки` теперь не только запускает проверки руками, но и управляет scheduler и показывает history-слой.
- alerting имеет собственные настройки, stale-правило и журнал доставок.
- внешние уведомления доставляются через Telegram и SMTP email, если каналы заданы в env/Portainer.
- reminders отправляются только для активных alerts, у которых истёк `reminder_interval_seconds`.
