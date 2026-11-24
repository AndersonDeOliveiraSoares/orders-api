
import json
import logging
import threading

import pika
from sqlalchemy.dialects.postgresql import insert

from app.database.database_connection import SessionLocal
from app.messaging.rabbitmq_connection import RabbitMQConnection
from app.models.models_processed_event import ProcessedEvent

logger = logging.getLogger(__name__)


class RabbitMQConsumer:

    def __init__(
        self,
        rabbitmq_connection=None,
        exchange="orders",
        queue="orders.events",
        routing_key="order.created",
        session_factory=SessionLocal,
    ):
        self.rabbitmq = rabbitmq_connection or RabbitMQConnection()

        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.session_factory = session_factory

        self.channel = None
        self.stop_event = threading.Event()

    def connect(self):
        self.channel = self.rabbitmq.connect()

        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type="direct",
            durable=True,
        )

        self.channel.queue_declare(
            queue=self.queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "orders.dlx",
                "x-dead-letter-routing-key": "orders.dead",
            },
        )

        self.channel.queue_bind(
            exchange=self.exchange,
            queue=self.queue,
            routing_key=self.routing_key,
        )

        logger.info(
            "RabbitMQ Consumer conectado",
            extra={"queue": self.queue},
        )

    def process_message(self, body: bytes) -> dict:
        message = json.loads(body)

        if not isinstance(message, dict):
            raise ValueError("O conteúdo da mensagem deve ser um objeto JSON.")

        event_id = message.get("event_id")

        if event_id is None or str(event_id).strip() == "":
            raise ValueError("Mensagem sem event_id.")

        logger.info(
            "Evento recebido",
            extra={
                "event_id": event_id,
                "event_type": message.get("event_type"),
                "aggregate_type": message.get("aggregate_type"),
                "aggregate_id": message.get("aggregate_id"),
                "correlation_id": message.get("correlation_id"),
            },
        )

        return message

    def register_processed_event(self, db, event_id: str) -> bool:
        statement = (
            insert(ProcessedEvent)
            .values(event_id=str(event_id))
            .on_conflict_do_nothing(
                index_elements=[ProcessedEvent.event_id],
            )
            .returning(ProcessedEvent.id)
        )

        result = db.execute(statement)

        registered_id = result.scalar_one_or_none()

        if registered_id is None:
            logger.info(
                "Evento já processado. Ignorando duplicidade.",
                extra={"event_id": event_id},
            )
            return False

        return True

    def process_event(self, db, message: dict):
        """
        Ponto de entrada para as operações de negócio do evento.

        As operações futuras devem utilizar esta mesma sessão db,
        para compartilhar a transação com o registro de idempotência.
        """
        pass

    def on_message(self, channel, method, properties, body):
        retry_count = self._get_retry_count(properties)

        try:
            message = self.process_message(body)

            event_id = message["event_id"]

            with self.session_factory.begin() as db:
                is_new_event = self.register_processed_event(
                    db,
                    event_id,
                )

                if is_new_event:
                    self.process_event(db, message)

            if not is_new_event:
                channel.basic_ack(
                    delivery_tag=method.delivery_tag,
                )

                logger.info(
                    "Mensagem duplicada confirmada (ACK)",
                    extra={"event_id": event_id},
                )
                return

        except json.JSONDecodeError:
            logger.exception("Mensagem JSON inválida")

            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )

            logger.warning("Mensagem inválida encaminhada para DLQ")
            return

        except Exception:
            logger.exception("Erro ao processar mensagem")

            if retry_count < 2:
                try:
                    self._publish_retry(properties, body)

                    channel.basic_ack(
                        delivery_tag=method.delivery_tag,
                    )

                    logger.warning(
                        "Mensagem encaminhada para Retry",
                        extra={
                            "retry_count": retry_count + 1,
                            "max_retries": 2,
                        },
                    )

                except Exception:
                    logger.exception(
                        "Erro ao publicar mensagem no Retry"
                    )

                    channel.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True,
                    )

                    logger.warning(
                        "Mensagem devolvida à fila para nova tentativa"
                    )

            else:
                channel.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=False,
                )

                logger.error(
                    "Limite de tentativas atingido. Mensagem enviada à DLQ",
                    extra={
                        "retry_count": retry_count,
                        "max_retries": 2,
                    },
                )

            return

        channel.basic_ack(
            delivery_tag=method.delivery_tag,
        )

        logger.info("Mensagem confirmada (ACK)")

    def _publish_retry(self, properties, body: bytes):
        connection = RabbitMQConnection()

        condition = threading.Condition()

        publish_state = {
            "tag": None,
            "confirmed": False,
            "rejected": False,
            "returned": False,
        }

        def on_confirm(method_frame):
            method = method_frame.method

            with condition:
                if isinstance(method, pika.spec.Basic.Ack):
                    publish_state["confirmed"] = True

                elif isinstance(method, pika.spec.Basic.Nack):
                    publish_state["rejected"] = True

                condition.notify_all()

        def on_publish(delivery_tag):
            with condition:
                publish_state["tag"] = delivery_tag
                condition.notify_all()

        def on_return(channel, method, returned_properties, returned_body):
            with condition:
                publish_state["returned"] = True
                condition.notify_all()

        try:
            channel = connection.connect()

            channel.add_on_return_callback(on_return)

            channel.confirm_delivery(
                ack_nack_callback=on_confirm,
            )

            headers = dict(
                properties.headers or {}
            ) if properties else {}

            retry_count = self._get_retry_count(properties)

            headers["x-retry-count"] = retry_count + 1

            channel.basic_publish(
                exchange="orders.retry.exchange",
                routing_key="orders.retry",
                body=body,
                properties=pika.BasicProperties(
                    headers=headers,
                    delivery_mode=2,
                    content_type=(
                        properties.content_type
                        if properties and properties.content_type
                        else "application/json"
                    ),
                ),
                mandatory=True,
                on_publish=on_publish,
            )

            with condition:
                confirmed = condition.wait_for(
                    lambda: (
                        publish_state["tag"] is not None
                        and (
                            publish_state["confirmed"]
                            or publish_state["rejected"]
                        )
                    ),
                    timeout=30,
                )

                if not confirmed:
                    raise TimeoutError(
                        "Tempo esgotado aguardando confirmação do Retry."
                    )

                if publish_state["rejected"]:
                    raise RuntimeError(
                        "RabbitMQ rejeitou a publicação do Retry."
                    )

                if publish_state["returned"]:
                    raise RuntimeError(
                        "RabbitMQ devolveu a mensagem de Retry."
                    )

            logger.info(
                "Publicação no Retry confirmada",
                extra={
                    "retry_count": retry_count + 1,
                },
            )

        finally:
            connection.close()

    def start(self):
        self.stop_event.clear()

        try:
            self.connect()

            self.channel.basic_qos(
                prefetch_count=1,
            )

            self.channel.basic_consume(
                queue=self.queue,
                on_message_callback=self.on_message,
                auto_ack=False,
            )

            logger.info(
                "Consumidor aguardando mensagens",
                extra={"queue": self.queue},
            )

            self.stop_event.wait()

        except KeyboardInterrupt:
            logger.info("Solicitado encerramento do consumidor")

        finally:
            self.close()

    def close(self):
        self.stop_event.set()

        if self.rabbitmq.connection:
            self.rabbitmq.close()

        logger.info("Consumidor encerrado")

    def _get_retry_count(self, properties) -> int:
        if properties is None:
            return 0

        headers = properties.headers or {}

        try:
            return int(headers.get("x-retry-count", 0))
        except (TypeError, ValueError):
            return 0
