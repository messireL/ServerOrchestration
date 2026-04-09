# Архитектура проекта

## Актуальное решение
- GitHub — основной источник кода проекта.
- Portainer — основной путь deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback и диагностика.
- Контейнеры приложения должны быть non-root.
- PostgreSQL хранит inventory, состояние проверок, задания и историю.
- Быстрые проверки (`ping`, HTTP/HTTPS probe, порты, 3x-ui console/subscription) идут отдельным probe-слоем, не через Ansible.
- Ansible используется как исполнительный слой для операций изменения: apt, timezone, reboot, 3x-ui update/restart, сбор журналов и т.п.

## Важный нюанс Portainer
Stack из Git-репозитория в Portainer лучше использовать с уже готовыми image из registry.
Для этого в проект добавлен GitHub Actions workflow, который публикует backend image в GHCR.
