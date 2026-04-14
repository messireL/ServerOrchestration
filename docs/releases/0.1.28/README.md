# Release v0.1.28

## Что вошло
- Portainer stack backend image переведён с version tag на стабильный operational tag `stable`;
- GitHub Actions workflow GHCR публикует backend image с тегами `stable` и `<VERSION>`;
- в stack env/example и compose добавлены `BACKEND_IMAGE`, `BACKEND_RELEASE_VERSION`, `BACKEND_RELEASE_CHANNEL`;
- в compose добавлены labels release/channel для прозрачности в Portainer;
- документация и transfer-package синхронизированы под новый runtime-подход.

## Главный смысл релиза
Перевести прод/runtime-контур на один стабильный backend image tag без постоянного переключения compose на новую версию образа при каждом релизе, сохранив при этом version tags в registry для истории и rollback.
