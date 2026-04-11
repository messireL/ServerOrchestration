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

## Актуальное уточнение v0.1.15
- inventory сервера хранит `web_url` и флаг `has_http_monitoring`;
- probe-слой умеет:
  - ICMP ping;
  - TCP connect к SSH-порту;
  - HTTP/HTTPS запрос к `web_url` с browser-like headers;
- результаты probe-проверок пишутся в `server_status`;
- активные alerts поднимаются отдельно по типам `ping_down`, `ssh_down`, `http_down`;
- HTTP/HTTPS проверка доступности не является заменой SSL-проверки и не является заменой отдельной логики для 3x-ui subscription.

## Важный нюанс Portainer
Stack из Git-репозитория в Portainer лучше использовать с уже готовыми image из registry.
Для этого в проект добавлен GitHub Actions workflow, который публикует backend image в GHCR.
