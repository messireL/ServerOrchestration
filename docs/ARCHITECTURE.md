# Архитектура проекта

## Актуальное решение
- GitHub — основной источник кода проекта.
- Portainer — основной путь deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback и диагностика.
- Контейнеры приложения должны быть non-root.
- PostgreSQL хранит inventory, состояние проверок, alerts, задания и историю.
- Быстрые проверки (`ping`, `SSH`, `HTTP/HTTPS`, затем 3x-ui console/subscription) идут отдельным probe-слоем, не через Ansible.
- Ansible используется как исполнительный слой для операций изменения: apt, timezone, reboot, 3x-ui update/restart, сбор журналов и т.п.

## Актуальное уточнение v0.1.22
- inventory сервера хранит `web_url` и флаг `has_http_monitoring`;
- probe-слой умеет:
  - ICMP ping;
  - TCP connect к SSH-порту;
  - HTTP/HTTPS запрос к `web_url` с browser-like headers;
- результаты probe-проверок пишутся в `server_status`;
- startup выполняет schema-sync legacy-колонок `servers` и `server_status`, чтобы probe-слой не падал на старой БД;
- backend image для non-root ping выставляет `setcap cap_net_raw=+ep` на системный `ping`;
- compose для backend добавляет `cap_add: NET_RAW`, чтобы ICMP не упирался в `Operation not permitted`;
- endpoint `/api/probes/ping/diagnostics` остаётся обязательным быстрым средством диагностики контейнера;
- UI теперь разделён на более чистые рабочие зоны: inventory, группы, проверки, alerts и roadmap;
- inventory-экран поддерживает быстрые фильтры по включённым серверам, проблемам, alerts и HTTP-monitoring;
- список серверов и экран проверок ориентированы на операторский сценарий: быстро увидеть статус, последнюю проверку и хвост ошибки без провала в сырой JSON.
