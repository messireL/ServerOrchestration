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
- Версия: `0.1.4`

## Что входит в v0.1.4
- backend API на FastAPI
- PostgreSQL
- таблицы inventory, `server_status` и `alerts`
- health/version endpoints
- стартовые inventory endpoints
- read-only web dashboard на `/`
- ручной запуск ping probe из web-интерфейса и API
- сохранение результата ping в `server_status`
- заготовка alerting по событию `ping_down`
- Portainer stack из Git-репозитория
- GitHub Actions workflow для публикации backend image в GHCR

## Что пока не делаем вручную
- серверы пока не заводим через API/curl в рабочем контуре;
- отдельный экран добавления/редактирования серверов будет следующим шагом;
- текущий web-интерфейс в `v0.1.4` — это foundation для просмотра статусов, alerts и запуска ping probe.

## Структура
- `app/backend` — исходники backend
- `deploy` — stack для Portainer
- `docs` — документация проекта и релизов
- `.github/workflows` — публикация backend image в GHCR
- `VERSION` — версия текущего релиза

## Важное по Portainer и GHCR
- В Portainer stack не требует вручную задавать `APP_VERSION` и `BACKEND_IMAGE`.
- image backend зафиксирован в compose на релиз `0.1.4`.
- Базовая timezone проекта по умолчанию: `Europe/Moscow`.
