# ServerOrchestration

ServerOrchestration — проект оркестрации управления Ubuntu-серверами с web GUI, PostgreSQL, scheduler/probe-слоем, alerting и исполнительным контуром для серверных операций.

## Базовые принципы
- GitHub — основной источник кода.
- Portainer — основной способ deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback/диагностика.
- Контейнеры приложения должны работать не от root.
- Каждый релиз имеет собственную версию и папку `docs/releases/<version>/`.

## Текущий релиз
- Версия: `0.1.1`

## Что входит в v0.1.1
- backend API на FastAPI
- PostgreSQL
- таблицы inventory и `server_status`
- health/version endpoints
- стартовые inventory endpoints
- Portainer stack из Git-репозитория
- GitHub Actions workflow для публикации backend image в GHCR

## Структура
- `app/backend` — исходники backend
- `deploy` — stack для Portainer
- `docs` — документация проекта и релизов
- `.github/workflows` — публикация backend image в GHCR
