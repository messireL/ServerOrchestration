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
- Версия: `0.1.8`

## Что входит в v0.1.8
- backend API на FastAPI
- PostgreSQL
- таблицы inventory, `server_status` и `alerts`
- health/version endpoints
- inventory endpoints для серверов, групп и связей
- ping probe и запись результата в `server_status`
- заготовка alerting по событию `ping_down`
- UI переработан в более спокойном и читабельном стиле с обновлённой типографикой, более чистой светлой темой и левым меню с отдельными разделами:
  - Главная
  - Серверы
  - Группы
  - Проверки
  - Оповещения
  - Дальше
- web-формы для добавления серверов и групп
- web-форма привязки сервера к группе
- Portainer stack из Git-репозитория
- GitHub Actions workflow для публикации backend image в GHCR

## Что уже можно делать через веб-интерфейс
- смотреть dashboard и summary
- создавать группы
- добавлять серверы
- привязывать серверы к группам
- запускать ping probe
- смотреть статусы и alerts по отдельным разделам

## Структура
- `app/backend` — исходники backend и встроенного web UI
- `deploy` — stack для Portainer
- `docs` — документация проекта и релизов
- `.github/workflows` — публикация backend image в GHCR
- `VERSION` — версия текущего релиза

## Важное по Portainer и GHCR
- В Portainer stack не требует вручную задавать `APP_VERSION` и `BACKEND_IMAGE`.
- image backend зафиксирован в compose на релиз `0.1.8`.
- Базовая timezone проекта по умолчанию: `Europe/Moscow`.
- Внешний URL панели задаётся через `APP_PUBLIC_BASE_URL` в env Portainer.
