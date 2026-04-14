# Deploy / Update v0.1.29

## Базовый сценарий Portainer
1. Обновить код стека/репозиторий до v0.1.29.
2. Убедиться, что backend image `ghcr.io/messirel/serverorchestration-backend:stable` опубликован/доступен.
3. Выполнить redeploy stack с подтягиванием свежего image.

## Env для обычного deploy
```dotenv
BACKEND_IMAGE=ghcr.io/messirel/serverorchestration-backend:stable
BACKEND_RELEASE_CHANNEL=stable
```

`BACKEND_RELEASE_VERSION` остаётся опциональным: можно не задавать, если используется обычный ручной redeploy `stable` в Portainer.
