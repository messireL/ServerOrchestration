# ServerOrchestration — перенос в новый чат

## Что это
ServerOrchestration — панель оркестрации и мониторинга серверов: SSH, HTTP/HTTPS, SSL, 3x-ui console/subscription, история прогонов, группировка серверов и дальнейший operational/Ansible-контур.

## Текущий пакет
- Версия архива: **v0.1.51**
- Версия в `VERSION`: **0.1.51**
- Версия backend (`APP_VERSION`): **0.1.51**
- Стек: **FastAPI + PostgreSQL + Docker Compose + Vanilla JS/AJAX**

## Что уже сделано к этому шагу
1. Кнопки ручных проверок возвращены в стабильный AJAX/static-контур без хрупкой frontend-магии.
2. Разведены сценарии:
   - SSH endpoint;
   - Web URL;
   - 3x-ui console URL;
   - 3x-ui subscription URL;
   - SSL по subscription/целевому порту, не по SSH-порту.
3. Починена SSL-проверка для self-signed и обычных сертификатов.
4. В мониторинге появились отдельные статусы по HTTP / 3x-ui console / 3x-ui subscription / SSL.
5. Таблица проверок уже приведена в более читаемый вид через плашки и компактные детали.
6. Страница подписки 3x-ui теперь разбирается как HTML-страница браузера, а не только как «голый» payload.
7. В **v0.1.51** усилен парсинг subscription page:
   - убран ложный захват заголовка страницы и обрывков HTML/JS как данных профиля;
   - добавлен отдельный line-based fallback для пар `label -> value`;
   - улучшен script fallback для JS-объектов вида `subId: "...", download: "..."`;
   - добавлены unit-тесты parser fallback.

## Что входит в v0.1.51
- Усилен backend-парсинг subscription HTML/JS.
- Добавлена защита от мусорных значений, похожих на HTML-разметку и inline-script.
- Нормализованы поля профиля:
  - `subscription_id`
  - `profile_status`
  - `downloaded_bytes`
  - `uploaded_bytes`
  - `used_bytes`
  - `total_bytes`
  - `remaining_bytes`
  - `last_seen_text`
  - `expires_text`
  - `expires_unlimited`
- Если страница не отдаёт `used/remaining` напрямую, backend пытается вычислить их из `upload/download/total`.

## Что проверить после выкладки
1. Кнопки `Проверить SSH`, `Проверить HTTP/HTTPS`, `Проверить 3x-ui`, `Проверить SSL`, `Запустить все проверки` нажимаются без JS-сбоев.
2. Для сервера с 3x-ui в деталях subscription появляются:
   - использование трафика;
   - общий лимит;
   - остаток;
   - срок действия / бессрочность;
   - last seen / статус / subscription id.
3. Вместо куска HTML больше не показывается мусорный хвост страницы.
4. SSL-проверка отдельно продолжает работать и не ломается на self-signed сертификате.
5. История прогонов сохраняет результаты без регрессии.
6. Версия в UI и `/health` соответствует `0.1.51`.

## Важные файлы
- `app/backend/src/main.py` — API, scheduler, ручные проверки
- `app/backend/src/probes.py` — логика probe-контуров, SSL, 3x-ui, парсинг subscription
- `app/backend/tests/test_subscription_html_parser.py` — unit-тесты проблемных сценариев подписки
- `app/backend/src/db.py` — хранение серверов, статусов и summary/details
- `app/backend/src/static/app.js` — стабильный AJAX frontend
- `app/backend/src/static/styles.css` — таблицы/плашки/hover
- `deploy/docker-compose.portainer.yml` — stack для Portainer
- `deploy/stack.env.example` — env-пример
- `docs/releases/0.1.51/RELEASE_NOTES.md` — заметки по текущему релизу

## Текущий приоритет дальше
Главный курс — **меньше латания косметики, больше функционала**.

Ближайший рабочий план:
1. Проверить v0.1.51 на живой странице подписки 3x-ui: должны появляться usage/limit/expire/status/last seen без куска HTML.
2. Если у части подписок поля всё ещё пустые — сохранить HTML-ответ целиком и добить конкретный шаблон 3x-ui адресно.
3. Разгрузить экран `Администрирование → Безопасность → Диагностика`: меньше сваленных блоков, лучше группировка проверок.
4. Перейти к следующим functional release monitoring/operational-контура.
5. Не забывать про остальной функционал **Ansible** — мониторинг не должен съесть весь проект.

## Как стартовать новый чат
Вставить так:

> Продолжаем проект ServerOrchestration.
> Базовый архив: v0.1.51.
> Смотри `docs/TRANSFER_TO_NEW_CHAT.md` и `docs/releases/0.1.51/RELEASE_NOTES.md`.
> Текущий фокус: проверить живой парсинг профиля подписки 3x-ui и затем вернуться к функциональному monitoring/Ansible-контуру.
