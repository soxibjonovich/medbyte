# notifications

User notifications and email reminders. Talks to `database` over HTTP; owns no DB tables itself.

Email requires `SMTP_HOST` (and optionally `SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) to be set.
A RabbitMQ consumer turns scheduled feedback-request messages into email reminders.
