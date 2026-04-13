# Bugs / notes for 0.1.24

- SMTP/Telegram требуют корректных env-переменных в Portainer, иначе доставки будут `skipped` или `failed`;
- в этом релизе нет acknowledge/mute из GUI: фокус именно на rules + delivery;
- если channels не заданы, alerting остаётся рабочим внутри панели, но внешние уведомления не отправляются.
