# Deploy 0.1.4

## Порядок
1. Обновить локальный репозиторий файлами релиза.
2. Сделать commit и push в GitHub.
3. Дождаться GitHub Actions публикации image `ghcr.io/messirel/serverorchestration-backend:0.1.4`.
4. В Portainer выполнить redeploy stack из Git.
5. Проверить `/health`, `/version`, `/api/summary`, `/api/status/servers`, `/api/alerts`, `/`.

## Env для Portainer
- `POSTGRES_PASSWORD`
- `APP_NAME=server-orchestration`
- `APP_TZ=Europe/Moscow`
- `POSTGRES_DB=orchestrator`
- `POSTGRES_USER=orchestrator`
- `BACKEND_BIND_IP=127.0.0.1`
- `BACKEND_PORT=18080`
