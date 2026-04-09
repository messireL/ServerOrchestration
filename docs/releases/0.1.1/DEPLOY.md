# Deploy 0.1.1

## Рекомендуемый путь
1. Залить код в GitHub репозиторий.
2. Дождаться завершения GitHub Actions workflow `Publish backend image to GHCR`.
3. При необходимости сделать package public в GHCR.
4. В Portainer:
   - Stacks
   - Add stack
   - Git Repository
   - Repository URL: `https://github.com/messireL/ServerOrchestration.git`
   - Repository reference: `refs/heads/main`
   - Compose path: `deploy/docker-compose.portainer.yml`
5. В Portainer задать переменные:
   - `APP_NAME=server-orchestration`
   - `APP_VERSION=0.1.1`
   - `APP_TZ=UTC`
   - `POSTGRES_DB=orchestrator`
   - `POSTGRES_USER=orchestrator`
   - `POSTGRES_PASSWORD=<свой_пароль>`
   - `BACKEND_IMAGE=ghcr.io/messirel/serverorchestration-backend:0.1.1`
   - `BACKEND_BIND_IP=127.0.0.1`
   - `BACKEND_PORT=18080`
6. Deploy the stack.

## Fallback
Если нужно диагностически поднять проект без Portainer:
- скопировать `deploy/stack.env.example` в `deploy/stack.env`
- заполнить значения
- запустить `docker compose -f deploy/docker-compose.local.yml --env-file deploy/stack.env up -d --build`
