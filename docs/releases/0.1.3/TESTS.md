# Tests 0.1.3

Проверить:
- GitHub Actions успешно публикует image `ghcr.io/messirel/serverorchestration-backend:0.1.3`
- Portainer stack deploy проходит без переменной `BACKEND_IMAGE`
- `/health` возвращает `database=true`
- `/version` возвращает `timezone=Europe/Moscow`
- `/api/summary` доступен
