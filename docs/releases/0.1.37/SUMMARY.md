# ServerOrchestration v0.1.37

## Что вошло
- исправлена SSL-проверка на Python 3.12+;
- убран вызов `ssl.match_hostname`, из-за которого SSL batch падал с `module 'ssl' has no attribute 'match_hostname'`;
- добавлено собственное сопоставление hostname/IP по SAN/CN;
- self-signed сертификаты теперь проверяются по сроку действия и совпадению hostname/IP, а не режутся из-за отсутствующего API.

## Проверка
1. Запустить `Проверить SSL`.
2. Убедиться, что в истории больше нет ошибки `module 'ssl' has no attribute 'match_hostname'`.
3. Для self-signed сертификата должен вернуться осмысленный результат: valid / expired / hostname mismatch.
