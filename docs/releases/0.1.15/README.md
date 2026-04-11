# Release 0.1.15

## Что добавлено
- SSH port checks
- HTTP/HTTPS availability checks по `web_url`
- новые поля inventory: `web_url`, `has_http_monitoring`
- новые статусы в `server_status`: `ssh_ok`, `ssh_latency_ms`, `http_ok`, `http_status_code`, `http_response_ms`
- alerts по типам `ssh_down` и `http_down`

## Зачем
Этот релиз закрывает базовый контур доступности до подключения 3x-ui и operational-задач через Ansible.
