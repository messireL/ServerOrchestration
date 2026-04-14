# ServerOrchestration

Web-панель мониторинга и операционного управления Ubuntu/Linux-серверами.

Текущий подготовленный релиз: **v0.1.32**.
Последний подтверждённый пользователем рабочий релиз: **v0.1.23**.

## Что уже есть в v0.1.32
- hotfix v0.1.32: устранён критичный crash backend на старте из-за импорта несуществующего `run_xui_check`;
- довосстановлены импорты в probe-контуре (`urlparse`, `datetime/timezone`, `Any`, `Dict`), чтобы SSL/3x-ui контур не падал уже на загрузке приложения;
- сохранён сценарий, где 3x-ui и SSL проверяются по `subscription_3xui_url` и её порту, отдельно от SSH;
- inventory серверов и групп;
- ping / SSH / HTTP проверки;
- scheduler фоновых проверок с хранением настроек и истории в PostgreSQL;
- alerting + stale monitoring + доставки уведомлений;
- отдельные URL для `console_3xui_url` и `subscription_3xui_url`;
- левое меню и разнесение экранов по разделам.

## Архитектурный стек
- FastAPI backend
- PostgreSQL
- статический frontend внутри backend
- Docker / Docker Compose
- Portainer как основной путь deploy/update
- Ansible как будущий исполнительный слой для операций изменения состояния сервера

## Документация
- ТЗ: `docs/TZ.md`
- Архитектура: `docs/ARCHITECTURE.md`
- Регламент релизов: `docs/RELEASE_POLICY.md`
- Перенос в новый чат: `docs/TRANSFER_TO_NEW_CHAT.md`
- Материалы по релизам: `docs/releases/<version>/`

## Ближайший следующий блок
- **v0.1.32** — startup/import hotfix для backend + стабилизация SSL/3x-ui контура
- затем журналы probe-run, операционная диагностика, timezone checks, apt/update flows, reboot actions, maintenance windows
