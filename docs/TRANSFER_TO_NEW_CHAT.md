# ServerOrchestration — перенос в новый чат

## Проект
- Название: **ServerOrchestration**
- Назначение: web-панель мониторинга и операционного управления Ubuntu/Linux-серверами
- Стек: **FastAPI + PostgreSQL + Docker Compose + Portainer**
- Основной путь deploy/update: **GitHub -> Portainer Stack**
- Fallback/диагностика: `docker compose`

## Текущее состояние
- Последний подтверждённый пользователем рабочий релиз: **v0.1.23**
- Текущий подготовленный релиз в этом архиве: **v0.1.29**
- Главный приоритет пользователя: **меньше UI-полировки, больше функциональных релизов мониторинга и operational-контура**

## Что уже реализовано к v0.1.29
- hotfix v0.1.29: исправлен HTTP probe persistence path; рассинхрон `http_ok/http_status_code/http_response_ms` → `ok/status_code/response_ms` устранён;
- inventory серверов и групп;
- ping / SSH / HTTP проверки;
- scheduler фоновых проверок с историей прогонов;
- alerting + stale monitoring + журналы доставок;
- 3x-ui проверки:
  - поля `console_3xui_url` и `subscription_3xui_url`;
  - отдельные статусы, HTTP-коды и latency;
  - отдельные `xui_interval_seconds` и `xui_timeout_seconds`;
  - отдельный scheduler-run по 3x-ui;
  - infra: Portainer stack переведён на стабильный backend image tag `stable`, workflow GHCR публикует `stable` + version tag, а stack хранит release markers отдельно;
- встроенные DB-модификации без ручного SQL для старой схемы.

## Что важно помнить в следующем чате
- ручные правки на сервере и ручные SQL-миграции нужно исключать; изменения должны приезжать релизом;
- для этого проекта в каждом релизе нужно поддерживать документацию в `docs/`;
- если меняется inventory / status / scheduler / alerting — проверять совместимость со старой БД;
- Portainer — основной сценарий deploy/update;
- UI уже разнесён по левому меню, дальше приоритет на функциональность, а не косметику.

## Что проверить после выкладки v0.1.29
1. В Portainer backend image по stack env/compose идёт как `ghcr.io/messirel/serverorchestration-backend:stable`.
2. Контейнер backend остаётся тем же по имени, без плодящихся version-tag image references в stack compose.
3. Канал `stable` используется для backend image; `APP_RELEASE_VERSION`/`BACKEND_RELEASE_VERSION` — опциональный release marker и не обязателен для deploy.
4. `/health` и `/version` отвечают штатно.
5. Главная и Проверки продолжают работать без регрессии после перехода на stable tag.

## Следующий логичный релиз
- **v0.1.30 — SSL checks**
  - срок действия сертификата;
  - остаток дней;
  - статус валиден / истекает / просрочен;
  - отображение в summary, status и alerts.
