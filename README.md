# ServerOrchestration

Web-панель мониторинга и операционного управления Ubuntu/Linux-серверами.

Текущий подготовленный релиз: **v0.1.28**.
Последний подтверждённый пользователем рабочий релиз: **v0.1.23**.

## Что уже есть в v0.1.28
- inventory серверов и групп;
- ping / SSH / HTTP проверки;
- scheduler фоновых проверок с хранением настроек и истории в PostgreSQL;
- alerting + stale monitoring + доставки уведомлений;
- 3x-ui checks:
  - отдельные URL для `console_3xui_url` и `subscription_3xui_url`;
  - отдельные статусы, HTTP-коды и время ответа;
  - отдельный scheduler-контур для 3x-ui без ручных SQL-правок по БД;
  - infra: backend image для Portainer переведён на стабильный тег `stable`, добавлены release markers в stack env/labels и обновлён publish workflow GHCR;
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
- **v0.1.29** — SSL checks
- затем timezone checks, apt/update flows, reboot actions, журналы, maintenance windows
