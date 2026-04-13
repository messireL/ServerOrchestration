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

## Актуальное уточнение v0.1.21
- inventory сервера хранит `web_url` и флаг `has_http_monitoring`;
- probe-слой умеет:
  - ICMP ping;
  - TCP connect к SSH-порту;
  - HTTP/HTTPS запрос к `web_url` с browser-like headers;
- результаты probe-проверок пишутся в `server_status`;
- startup обязан выполнять schema-sync legacy-колонок `servers` и `server_status`, чтобы probe-слой не падал на старой БД;
- backend image для non-root ping выставляет `setcap cap_net_raw=+ep` на системный `ping`;
- compose для backend добавляет `cap_add: NET_RAW`, чтобы ICMP не упирался в "Operation not permitted";
- для быстрой диагностики добавлен endpoint `/api/probes/ping/diagnostics`, который показывает наличие `ping` в контейнере и self-test на `127.0.0.1`;
- активные alerts поднимаются отдельно по типам `ping_down`, `ssh_down`, `http_down`;
- HTTP/HTTPS проверка доступности не является заменой SSL-проверки и не является заменой отдельной логики для 3x-ui subscription.

## Важный нюанс Portainer
Stack из Git-репозитория в Portainer лучше использовать с уже готовыми image из registry.
Для этого в проект добавлен GitHub Actions workflow, который публикует backend image в GHCR.
При redeploy Portainer может пересоздавать service task/контейнеры с новыми именами; это не отдельный баг проекта, а особенность механики обновления stack/task.
