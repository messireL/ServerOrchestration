# ServerOrchestration — перенос в новый чат

## Проект
- Название: **ServerOrchestration**
- Назначение: web-панель мониторинга и операционного управления Ubuntu/Linux-серверами
- Стек: **FastAPI + PostgreSQL + Docker Compose + Portainer**
- Основной путь deploy/update: **GitHub -> Portainer Stack**
- Fallback/диагностика: `docker compose`

## Текущее состояние
- Последний подтверждённый пользователем рабочий релиз: **v0.1.23**
- Текущий подготовленный релиз в этом архиве: **v0.1.26**
- Главный приоритет пользователя: **меньше UI-полировки, больше функциональных релизов мониторинга и operational-контура**

## Что уже реализовано к v0.1.26
- inventory серверов и групп;
- ping / SSH / HTTP проверки;
- scheduler фоновых проверок с историей прогонов;
- alerting + stale monitoring + журналы доставок;
- 3x-ui проверки:
  - поля `console_3xui_url` и `subscription_3xui_url`;
  - отдельные статусы, HTTP-коды и latency;
  - отдельные `xui_interval_seconds` и `xui_timeout_seconds`;
  - отдельный scheduler-run по 3x-ui;
  - hotfix: восстановлен backend-вызов `_execute_xui_batch`, из-за которого scheduler больше не падает `NameError`;
- встроенные DB-модификации без ручного SQL для старой схемы.

## Что важно помнить в следующем чате
- ручные правки на сервере и ручные SQL-миграции нужно исключать; изменения должны приезжать релизом;
- для этого проекта в каждом релизе нужно поддерживать документацию в `docs/`;
- если меняется inventory / status / scheduler / alerting — проверять совместимость со старой БД;
- Portainer — основной сценарий deploy/update;
- UI уже разнесён по левому меню, дальше приоритет на функциональность, а не косметику.

## Что проверить после выкладки v0.1.26
1. В логах backend больше нет `NameError: _execute_xui_batch is not defined`.
2. В `Проверки` ручной запуск connectivity/http проходит без 500-ошибки.
3. Через 1-2 интервала scheduler появляются новые history-записи `scheduler` для `xui`.
4. `/api/status/servers` продолжает возвращать `console_3xui_*` и `subscription_3xui_*`.
5. На старой БД backend стартует без ручного SQL.

## Следующий логичный релиз
- **v0.1.27 — SSL checks**
  - срок действия сертификата;
  - остаток дней;
  - статус валиден / истекает / просрочен;
  - отображение в summary, status и alerts.
