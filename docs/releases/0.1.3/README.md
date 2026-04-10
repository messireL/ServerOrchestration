# Release 0.1.3

Portainer + GHCR hotfix and timezone default update.

## Что изменено
- backend image в `deploy/docker-compose.portainer.yml` теперь зафиксирован на `ghcr.io/messirel/serverorchestration-backend:0.1.3`
- переменная `BACKEND_IMAGE` больше не нужна в Portainer env
- базовая timezone проекта по умолчанию изменена на `Europe/Moscow`
- локальный compose и backend defaults синхронизированы с `Europe/Moscow`
- добавлены пояснения по ошибке `unauthorized` при pull из GHCR

## Зачем
Это убирает одну частую причину падения stack в Portainer и делает стартовую конфигурацию ближе к реальному рабочему режиму.
