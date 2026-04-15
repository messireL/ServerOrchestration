# ServerOrchestration — перенос в новый чат

## Что это
ServerOrchestration — панель оркестрации и мониторинга серверов: SSH, HTTP/HTTPS, SSL, 3x-ui console/subscription, история прогонов, группировка серверов и дальнейший operational/Ansible-контур.

## Текущий пакет
- Версия архива: **v0.1.50**
- Версия в `VERSION`: **0.1.50**
- Версия backend (`APP_VERSION`): **0.1.50**
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
6. Страница подписки 3x-ui теперь разбирается как HTML-страница браузера, а не только как «голый» payload:
   - разбор табличных полей профиля подписки;
   - fallback по плоскому тексту страницы;
   - fallback по embedded/script-данным.

## Что входит в v0.1.50
- Усилен backend-парсинг subscription HTML.
- Добавлен extractor на `HTMLParser` для профиля подписки.
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
   - last seen / статус.
3. SSL-проверка отдельно продолжает работать и не ломается на self-signed сертификате.
4. История прогонов сохраняет результаты без регрессии.
5. Версия в UI и `/health` соответствует `0.1.50`.

## Важные файлы
- `app/backend/src/main.py` — API, scheduler, ручные проверки
- `app/backend/src/probes.py` — логика probe-контуров, SSL, 3x-ui, парсинг subscription
- `app/backend/src/db.py` — хранение серверов, статусов и summary/details
- `app/backend/src/static/app.js` — стабильный AJAX frontend
- `app/backend/src/static/styles.css` — таблицы/плашки/hover
- `deploy/docker-compose.portainer.yml` — stack для Portainer
- `deploy/stack.env.example` — env-пример
- `docs/releases/0.1.50/RELEASE_NOTES.md` — заметки по текущему релизу

## Текущий приоритет дальше
Главный курс — **меньше латания косметики, больше функционала**.

Ближайший рабочий план:
1. Добить стабильный вывод subscription profile на реальном endpoint, если конкретный сервер отдаёт данные не в HTML/inline-script, а отдельным XHR.
2. Перейти к функциональным релизам monitoring/operational-контура.
3. Не забывать про остальной функционал **Ansible** — мониторинг не должен съесть весь проект.
4. Дальше разносить operational-функции по нормальным разделам/вкладкам левого меню.

## Как стартовать новый чат
Вставить так:

> Продолжаем проект ServerOrchestration.
> Базовый архив: v0.1.50.
> Смотри `docs/TRANSFER_TO_NEW_CHAT.md` и `docs/releases/0.1.50/RELEASE_NOTES.md`.
> Текущий фокус: добить чтение профиля подписки 3x-ui с реального endpoint браузерного типа и затем вернуться к функциональному monitoring/Ansible-контуру.
