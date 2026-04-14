# Release Notes — v0.1.40

## Что исправлено
- починен контур сохранения результатов 3x-ui probes: backend больше не падает на `unexpected 3x-ui probe error: update_3xui_status(...)`;
- в БД и `summary_json` теперь сохраняются детали console/subscription probes, включая `source`, `checked_at` и вложенные details;
- парсятся заголовки `Subscription-Userinfo`, `Profile-Title`, `Profile-Web-Page-URL`, `Support-URL`;
- по подписке в UI теперь можно увидеть трафик, срок/expiry и метаданные профиля;
- история прогонов получила полезные details для SSL и 3x-ui вместо пустого `—`.

## Что проверить после обновления
1. Нажать `Проверить 3x-ui` и убедиться, что по серверу с подпиской отображаются traffic/expiry, а в истории есть детали вместо пустого поля.
2. Нажать `Проверить SSL` и убедиться, что для self-signed сертификата отображаются CN / self-signed / срок действия.
3. Проверить, что в контейнерных логах больше нет ошибок вида `update_3xui_status(... unexpected keyword ...)`.
