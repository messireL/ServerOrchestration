# Deploy 0.1.20

## Основной сценарий
1. Запушить изменения в GitHub.
2. Дождаться публикации backend image `0.1.20` в GHCR.
3. В Portainer сделать redeploy существующего stack из Git.

## Важно
- не создавать новый stack на каждый релиз;
- redeploy делать поверх существующего stack;
- периодически чистить stopped containers / dangling images, если Portainer начинает захламлять хост.
