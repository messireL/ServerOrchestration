# GHCR и Portainer

## Почему возникает ошибка `unauthorized`
Portainer успешно читает private Git-репозиторий по Git credentials, но это **не означает**, что Docker engine автоматически получает право скачать private image из `ghcr.io`.

Для backend image проекта используется GitHub Container Registry (`ghcr.io`). Если пакет image private, для pull нужен отдельный доступ к registry пакетов.

## Рабочие варианты
1. Сделать package `ghcr.io/messirel/serverorchestration-backend` public.
2. Настроить отдельную аутентификацию к `ghcr.io` в Portainer/Docker с токеном для GitHub Packages.

## Что проще для старта
Самый простой стартовый вариант — сделать backend image public и оставить Git-репозиторий private.
