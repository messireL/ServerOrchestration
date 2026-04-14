# Deploy / Update v0.1.26

## Основной путь
- обновить существующий Portainer stack из Git-репозитория;
- не создавать новый stack под новый релиз;
- убедиться, что подтянут именно обновлённые image/tag/env проекта.

## Цель hotfix
После обновления backend не должен больше падать в фоне на `_execute_xui_batch is not defined`.
