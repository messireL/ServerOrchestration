# Проверка релиза v0.1.28

1. В Portainer у backend image отображается `ghcr.io/messirel/serverorchestration-backend:stable`.
2. Контейнер backend остаётся `server-orchestration-backend`.
3. Через inspect/environment видны `APP_RELEASE_VERSION=0.1.28` и `APP_RELEASE_CHANNEL=stable`.
4. `/health` и `/version` отвечают штатно.
5. Главная и Проверки открываются без ошибок.
