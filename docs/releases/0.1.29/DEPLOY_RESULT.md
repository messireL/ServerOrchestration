# Результат deploy/update v0.1.29

Ожидаемый результат после выкладки:
- сайт открывается штатно;
- HTTP probe не пишет `TypeError: update_http_status() got an unexpected keyword argument 'http_ok'`;
- HTTP reset/save path сохраняет статус без падения фонового контура;
- runtime продолжает использовать backend image channel `stable`.
