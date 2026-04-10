# Deploy 0.1.7

## Основной сценарий
1. Распаковать архив в локальный репозиторий.
2. Сделать commit и push в GitHub.
3. Дождаться GitHub Actions для image `0.1.7`.
4. В Portainer сделать Redeploy stack из Git.

## Env Portainer
- `POSTGRES_PASSWORD`
- `APP_NAME=server-orchestration`
- `APP_TZ=Europe/Moscow`
- `APP_PUBLIC_BASE_URL=http://192.168.5.22:18080`
- `POSTGRES_DB=orchestrator`
- `POSTGRES_USER=orchestrator`
- `BACKEND_BIND_IP=192.168.5.22`
- `BACKEND_PORT=18080`
