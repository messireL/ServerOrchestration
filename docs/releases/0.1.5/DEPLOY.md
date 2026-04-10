# Deploy 0.1.5

1. Распаковать архив релиза поверх локального репозитория.
2. Проверить, что обновились `VERSION`, `app/backend/src/static/*`, `app/backend/src/main.py`, `deploy/docker-compose.portainer.yml`, `README.md`, `docs/releases/0.1.5/*`.
3. Сделать commit и push в `main`.
4. Дождаться GitHub Actions публикации image `ghcr.io/messirel/serverorchestration-backend:0.1.5`.
5. В Portainer открыть stack и выполнить redeploy из Git.
6. Проверить `/health`, `/version`, `/api/summary` и открыть `/`.
