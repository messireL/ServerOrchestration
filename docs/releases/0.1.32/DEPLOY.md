# Deploy v0.1.32

## Основной сценарий
1. Запушить изменения в GitHub.
2. Дождаться публикации backend image.
3. В Portainer открыть существующий stack проекта.
4. Выполнить Redeploy / Update stack из Git.
5. После redeploy сразу открыть логи backend и убедиться, что нет `ImportError` / `NameError` на старте.

## Env
Обычный runtime-режим остаётся прежним:

```env
BACKEND_IMAGE=ghcr.io/messirel/serverorchestration-backend:stable
BACKEND_RELEASE_CHANNEL=stable
```
