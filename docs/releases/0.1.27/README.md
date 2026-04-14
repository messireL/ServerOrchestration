# Release v0.1.27

## Что вошло
- синхронизирована HTML-форма `monitorSettingsForm` с backend/settings для 3x-ui;
- добавлены поля `xui_interval_seconds` и `xui_timeout_seconds` в UI планировщика;
- в frontend добавлен безопасный helper для записи значений в form-fields без падения страницы, если форма временно не совпадает по полям;
- обновлены тексты панели проверок и release-docs.

## Главный смысл релиза
Убрать frontend-падение Главной страницы после добавления 3x-ui scheduler settings, чтобы UI больше не ловил `Cannot set properties of undefined (setting 'value')` на загрузке панели.
