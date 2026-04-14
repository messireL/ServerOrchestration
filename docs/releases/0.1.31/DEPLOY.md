# Deploy v0.1.31

## Основной сценарий
1. Запушить изменения в GitHub.
2. Убедиться, что workflow публикации backend image завершился успешно.
3. В Portainer открыть существующий stack проекта.
4. Выполнить Redeploy / Update stack из Git.
5. Не создавать новый stack под релиз.

## Env
Обычный runtime-режим остаётся прежним:

```env
BACKEND_IMAGE=ghcr.io/messirel/serverorchestration-backend:stable
BACKEND_RELEASE_CHANNEL=stable
```

`BACKEND_RELEASE_VERSION` по-прежнему можно не задавать для обычного redeploy stable-канала.
