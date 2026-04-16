# ServerOrchestration — перенос в новый чат

## Что это
ServerOrchestration — панель оркестрации и мониторинга серверов: SSH, HTTP/HTTPS, SSL, 3x-ui console/subscription, история прогонов, группировка серверов и дальнейший operational/Ansible-контур.

## Текущий пакет
- Версия архива: **v0.1.54**
- Версия в `VERSION`: **0.1.54**
- Версия backend (`APP_VERSION`): **0.1.54**
- Версия Docker build arg: **0.1.54**
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
6. Страница подписки 3x-ui разбирается как HTML-страница браузера, а не только как «голый» payload.
7. В **v0.1.51** усилен backend-парсинг subscription page.
8. В **v0.1.52** дочищено frontend-отображение subscription page:
   - строка подписки переведена на русский;
   - если профиль успешно разобран, UI больше не показывает `HTTP 200`, `html embedded`, `cfg` и прочий техмусор;
   - в деталях оставлены только понятные оператору поля: трафик, остаток, срок, статус, last seen и subscription id.
9. В **v0.1.53** исправлен packaging/version-sync хвост:
   - синхронизированы version-маркеры в runtime/build;
   - обновлены `Dockerfile` и `deploy/docker-compose.local.yml`;
   - из архива исключён `.pytest_cache`;
   - добавлен `.gitignore` для тестового и Python-кэша.

## Что входит в v0.1.53
- Всё из v0.1.52 по подпискам 3x-ui.
- Нормальный чистый архив без `.pytest_cache`.
- Синхронная версия `0.1.53` в runtime/build-файлах проекта.
- Обновлённая документация релиза.

## Что проверить после выкладки
1. В UI и `/health` версия = `0.1.53`.
2. В строке `Подписка 3x-ui` по-прежнему читаемые русские данные без `HTTP 200`, `html embedded` и прочего мусора, если профиль распарсен.
3. В архиве нет `.pytest_cache`.
4. Кнопки ручных проверок не сломались.

## Важные файлы
- `app/backend/src/main.py` — API, scheduler, ручные проверки
- `app/backend/src/probes.py` — логика probe-контуров, SSL, 3x-ui, парсинг subscription
- `app/backend/tests/test_subscription_html_parser.py` — unit-тесты проблемных сценариев подписки
- `app/backend/src/db.py` — хранение серверов, статусов и summary/details
- `app/backend/src/static/app.js` — стабильный AJAX frontend
- `app/backend/src/static/styles.css` — таблицы/плашки/hover
- `app/backend/Dockerfile` — backend image build/version env
- `deploy/docker-compose.local.yml` — локальный build-контур
- `deploy/docker-compose.portainer.yml` — stack для Portainer
- `docs/releases/0.1.54/RELEASE_NOTES.md` — заметки по текущему релизу

## Текущий приоритет дальше
Главный курс — **меньше UI-полировки, больше функционала**, но без мусора в интерфейсе и без рассыпания release-пакета.

Ближайший рабочий план:
1. Проверить v0.1.53 на живой странице подписки 3x-ui и на версии в runtime/UI.
2. Затем вернуться к разгрузке экрана `Администрирование → Безопасность → Диагностика`.
3. После этого идти дальше в monitoring/operational и Ansible-контур.

## Как стартовать новый чат
Вставить так:

> Продолжаем проект ServerOrchestration.
> Базовый архив: v0.1.54.
> Смотри `docs/TRANSFER_TO_NEW_CHAT.md` и `docs/releases/0.1.54/RELEASE_NOTES.md`.
> Текущий фокус: проверить новую operational-структуру вкладки `Проверки`, убедиться, что subscription profile 3x-ui по-прежнему читается чисто, затем идти в функциональный monitoring/Ansible-контур.
