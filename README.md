# Система мониторинга

Система мониторинга — проект оркестрации управления Ubuntu-серверами с web GUI, PostgreSQL, inventory, status/probe-слоем, alerts и будущим operational-контуром через Ansible.

## Базовые принципы
- GitHub — основной источник кода.
- Portainer — основной способ deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback/диагностика.
- Контейнеры приложения работают non-root.
- Каждый релиз имеет собственную версию и папку `docs/releases/<version>/`.

## Текущий релиз
- Версия: `0.1.16`

## Что входит в v0.1.16
- backend API на FastAPI;
- PostgreSQL;
- inventory, `server_status` и `alerts`;
- CRUD по серверам и группам через web UI;
- ping probe;
- проверка доступности SSH-порта;
- проверка HTTP/HTTPS по `web_url` с browser-like headers;
- hotfix по inventory-форме: поле `Web URL`, чекбокс `Проверять HTTP/HTTPS` и рабочая кнопка `Добавить сервер`;
- alerts по `ping_down`, `ssh_down`, `http_down`;
- web UI с левым меню, светлой и тёмной темой;
- Portainer stack из Git-репозитория;
- GitHub Actions workflow для публикации backend image в GHCR.

## Что уже можно делать через веб-интерфейс
- смотреть summary и dashboard;
- создавать, редактировать и удалять серверы;
- создавать, редактировать и удалять группы;
- создавать и удалять связи сервер ↔ группа;
- запускать ping / SSH / HTTP/HTTPS проверки;
- смотреть alerts и статусы по разделам.

## Роль Ansible
- Быстрые проверки (`ping`, `SSH`, `HTTP/HTTPS`) остаются в собственном probe-слое проекта.
- Ansible не используется как GUI и не используется для частого мониторинга.
- Ansible будет подключаться как исполнительный слой для apt, timezone, reboot, 3x-ui и operational-задач.
