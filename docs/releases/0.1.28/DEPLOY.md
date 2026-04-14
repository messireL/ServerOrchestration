# Deploy / Update v0.1.28

## Основной путь
- обновить существующий Portainer stack из Git-репозитория;
- compose теперь использует `BACKEND_IMAGE=ghcr.io/messirel/serverorchestration-backend:stable`;
- release markers хранятся отдельно как `BACKEND_RELEASE_VERSION` и `BACKEND_RELEASE_CHANNEL`.

## Что изменилось для оператора
- backend image tag в stack больше не нужно менять под каждую версию;
- для rollback можно временно переопределить `BACKEND_IMAGE` на конкретный version tag.
