# Архитектура проекта

## Актуальное решение
- GitHub — основной источник кода проекта.
- Portainer — основной путь deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback и диагностика.
- Контейнеры приложения должны быть non-root.
- PostgreSQL хранит inventory, состояние проверок, alerts, настройки scheduler и историю прогонов.
- Быстрые проверки (`ping`, `SSH`, `HTTP/HTTPS`, `3x-ui console`, `3x-ui subscription`) идут отдельным probe-слоем, не через Ansible.
- Ansible используется как исполнительный слой для операций изменения: apt, timezone, reboot, 3x-ui update/restart, сбор журналов и т.п.

## Актуальное уточнение v0.1.27
- inventory сервера хранит `web_url`, `console_3xui_url`, `subscription_3xui_url` и профильные флаги мониторинга;
- probe-слой умеет:
  - ICMP ping;
  - TCP connect к SSH-порту;
  - HTTP/HTTPS запрос к `web_url` с browser-like headers;
  - отдельные HTTP-проверки `3x-ui console` и `3x-ui subscription`;
- результаты probe-проверок пишутся в `server_status`;
- для 3x-ui отдельно сохраняются `*_ok`, `*_http_status`, `*_response_ms`;
- scheduler-настройки хранятся в таблице `monitor_settings`;
- интервалы и таймауты для 3x-ui вынесены отдельно от обычного HTTP;
- background scheduler поднимается вместе с backend и сам запускает due-проверки;
- последние scheduler-run по ping / SSH / HTTP / 3x-ui хранятся в БД;
- старые БД доводятся до актуальной схемы встроенными миграциями backend без ручных SQL-правок;
- экран `Проверки` управляет scheduler, ручными прогонами и показывает history-слой;
- alerting имеет собственные настройки, stale-правило и журнал доставок;
- внешние уведомления доставляются через Telegram и SMTP email, если каналы заданы в env/Portainer.

- hotfix v0.1.26 восстанавливает отсутствовавший backend batch-runner для 3x-ui, чтобы scheduler и manual probes не падали `NameError`.
- hotfix v0.1.27 синхронизирует frontend form-fields monitor settings с backend scheduler settings и добавляет безопасную запись значений в форму.
