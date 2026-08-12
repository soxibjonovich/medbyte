FROM rabbitmq:3.13-management-alpine

# rabbitmq_delayed_message_exchange is a community plugin, not bundled in the
# official image — bake it in so `rabbitmq-plugins enable --offline` at
# container start (see docker-compose.yml) can find it.
ADD https://github.com/rabbitmq/rabbitmq-delayed-message-exchange/releases/download/v3.13.0/rabbitmq_delayed_message_exchange-3.13.0.ez /opt/rabbitmq/plugins/
