# Deploy 0.1.3

## Portainer stack
- Repository URL: `https://github.com/messireL/ServerOrchestration.git`
- Reference: `refs/heads/main`
- Compose path: `deploy/docker-compose.portainer.yml`

## Обязательные env
- `POSTGRES_PASSWORD`

## Рекомендуемые env
- `APP_NAME=server-orchestration`
- `APP_TZ=Europe/Moscow`
- `POSTGRES_DB=orchestrator`
- `POSTGRES_USER=orchestrator`
- `BACKEND_BIND_IP=127.0.0.1`
- `BACKEND_PORT=18080`

## Важно
Если при deploy появляется `unauthorized` от `ghcr.io`, выполните один из двух вариантов:
1. Сделайте GHCR package backend public.
2. Настройте отдельную аутентификацию к `ghcr.io` в Docker/Portainer токеном для GitHub Packages.
