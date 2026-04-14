# Release v0.1.26

## Что вошло
- исправлен backend hotfix для 3x-ui scheduler/manual batch-run;
- в `main.py` добавлен фактический `_execute_xui_batch(...)` и runner по серверам;
- восстановлена запись history для `xui` source=`manual` и `scheduler`;
- сохранено обновление `server_status` через `update_3xui_status(...)`;
- обновлены release-docs и файл переноса в новый чат.

## Главный смысл релиза
Убрать падение фонового scheduler по `NameError`, чтобы 3x-ui проверки не были только на бумаге в UI/API, а реально выполнялись backend-ом после обычной выкладки через Portainer без ручных доправок на сервере.
