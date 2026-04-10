# Архитектура проекта

## Актуальное решение
- GitHub — основной источник кода проекта.
- Portainer — основной путь deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback и диагностика.
- Контейнеры приложения должны быть non-root.
- PostgreSQL хранит inventory, состояние проверок, alerts, задания и историю.
- Быстрые проверки (`ping`, HTTP/HTTPS probe, порты, 3x-ui console/subscription) идут отдельным probe-слоем, не через Ansible.
- Ansible используется как исполнительный слой для операций изменения: apt, timezone, reboot, 3x-ui update/restart, сбор журналов и т.п.

## Актуальное уточнение v0.1.4
- В проект добавлен базовый web dashboard на `/`.
- Dashboard сейчас read-only: показывает summary, статусы серверов, active alerts.
- Из dashboard можно вручную запускать `ping probe`.
- Результаты probe пишутся в `server_status`.
- При проблеме ping создаётся active alert типа `ping_down`, при восстановлении — alert переводится в `resolved`.
- Отдельный полноценный inventory UI для добавления/редактирования серверов будет следующим шагом.

## Важный нюанс Portainer
Stack из Git-репозитория в Portainer лучше использовать с уже готовыми image из registry.
Для этого в проект добавлен GitHub Actions workflow, который публикует backend image в GHCR.
