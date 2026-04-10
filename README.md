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
- Версия: `0.1.3`

## Что входит в v0.1.3
- backend API на FastAPI
- PostgreSQL
- таблицы inventory и `server_status`
- health/version endpoints
- стартовые inventory endpoints
- Portainer stack из Git-репозитория
- GitHub Actions workflow для публикации backend image в GHCR
- hotfix для Portainer env: безопасные значения по умолчанию и отсутствие обязательной `APP_VERSION` в stack variables

## Структура
- `app/backend` — исходники backend
- `deploy` — stack для Portainer
- `docs` — документация проекта и релизов
- `.github/workflows` — публикация backend image в GHCR
- `VERSION` — версия текущего релиза


## Важное по Portainer и GHCR
- В Portainer stack больше не требует переменную `BACKEND_IMAGE`: image backend зафиксирован в compose на релиз `0.1.3`.
- Если при deploy появляется `unauthorized` при pull из `ghcr.io`, это означает, что backend image недоступен анонимно и нужно либо сделать пакет GHCR public, либо настроить аутентификацию Portainer/Docker к `ghcr.io` отдельным токеном для пакетов.
- Базовая timezone проекта по умолчанию: `Europe/Moscow`.
