# Release Notes — v0.1.46

## Что исправлено
- исправлен runtime-crash `name '_parse_subscription_profile_from_html' is not defined`;
- в `probes.py` реально добавлены helper-функции HTML-парсинга профиля подписки, а не только вызов этих функций;
- сохранена логика объединения `html-embedded` и HTML-профиля подписки.

## Что проверить после обновления
1. Нажать `Проверить 3x-ui`.
2. Убедиться, что больше нет NameError по `_parse_subscription_profile_from_html`.
3. Проверить, что в ответе есть и `encoding: html-embedded`, и поля профиля подписки.
