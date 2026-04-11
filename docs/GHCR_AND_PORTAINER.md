# GHCR и Portainer

## Почему возникает ошибка `unauthorized`
Portainer успешно читает private Git-репозиторий по Git credentials, но это **не означает**, что Docker engine автоматически получает право скачать private image из `ghcr.io`.

Для backend image проекта используется GitHub Container Registry (`ghcr.io`). Если пакет image private, для pull нужен отдельный доступ к registry пакетов.

## Рабочие варианты
1. Сделать package `ghcr.io/messirel/serverorchestration-backend` public.
2. Настроить отдельную аутентификацию к `ghcr.io` в Portainer/Docker с токеном для GitHub Packages.

## Что проще для старта
Самый простой стартовый вариант — сделать backend image public и оставить Git-репозиторий private.

## Почему в Portainer после redeploy контейнер может выглядеть "новым"
Если stack разворачивается через Portainer stack/swarm-механику, Docker пересоздаёт service task на новый image/tag. Из-за этого:
- container ID меняется на каждом redeploy;
- task/container name тоже может отличаться;
- `container_name` в swarm-режиме не является жёсткой гарантией имени;
- старые stopped-контейнеры могут оставаться до очистки.

Это не означает, что код сам плодит бесконечные контейнеры. Обычно это следствие стандартного recreate/update процесса Portainer.

## Что делать, чтобы сервер не зарастал stopped-контейнерами
- использовать один и тот же stack name, а не создавать новый stack на каждый релиз;
- redeploy существующий stack, а не дублировать его;
- периодически чистить stopped-контейнеры и dangling images через Portainer prune или через Docker CLI;
- помнить, что смена image tag (`0.1.18` → `0.1.20`) почти всегда означает пересоздание контейнера.
