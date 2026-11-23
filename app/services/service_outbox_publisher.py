
import json
import logging
import threading

import pika

from app.database.database_connection import SessionLocal
from app.messaging.rabbitmq_connection import RabbitMQConnection
from app.repositories.repository_outbox import OutboxRepository


logger = logging.getLogger(__name__)


class OutboxPublisher:

    CONFIRM_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        session_factory=SessionLocal,
        rabbitmq_connection=None,
        exchange="orders",
        queue="orders.events",
        routing_key="order.created",
    ):
        self.session_factory = session_factory
        self.rabbitmq = rabbitmq_connection or RabbitMQConnection()

        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key

    def publish_pending_events(
        self,
        limit: int = 100,
        event_ids: list[int] | None = None,
    ) -> int:

        published_count = 0

        condition = threading.Condition()

        confirmed_tags = set()
        rejected_tags = set()

        publish_state = {
            "tag": None,
            "returned": False,
        }

        def on_confirm(method_frame):
            method = method_frame.method
            delivery_tag = method.delivery_tag

            with condition:
                if isinstance(method, pika.spec.Basic.Ack):
                    if method.multiple:
                        confirmed_tags.update(
                            tag for tag in range(1, delivery_tag + 1)
                        )
                    else:
                        confirmed_tags.add(delivery_tag)

                elif isinstance(method, pika.spec.Basic.Nack):
                    if method.multiple:
                        rejected_tags.update(
                            tag for tag in range(1, delivery_tag + 1)
                        )
                    else:
                        rejected_tags.add(delivery_tag)

                condition.notify_all()

        def on_publish(delivery_tag):
            with condition:
                publish_state["tag"] = delivery_tag
                condition.notify_all()

        def on_return(channel, method, properties, body):
            with condition:
                publish_state["returned"] = True
                condition.notify_all()

            logger.error(
                "RabbitMQ devolveu mensagem publicada",
                extra={
                    "exchange": self.exchange,
                    "routing_key": self.routing_key,
                },
            )

        logger.info(
            "Iniciando publicação de eventos da Outbox",
            extra={
                "limit": limit,
                "event_ids": event_ids,
            },
        )

        try:
            channel = self.rabbitmq.connect()

            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type="direct",
                durable=True,
            )

            channel.queue_declare(
                queue=self.queue,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "orders.dlx",
                    "x-dead-letter-routing-key": "orders.dead",
                },
            )

            channel.queue_bind(
                exchange=self.exchange,
                queue=self.queue,
                routing_key=self.routing_key,
            )

            channel.add_on_return_callback(on_return)

            channel.confirm_delivery(
                ack_nack_callback=on_confirm,
                timeout=self.CONFIRM_TIMEOUT_SECONDS,
            )

            with self.session_factory() as db:
                repository = OutboxRepository(db)

                events = repository.get_pending_events(
                    limit=limit,
                    event_ids=event_ids,
                )

                logger.info(
                    "Eventos pendentes encontrados",
                    extra={
                        "events_count": len(events),
                    },
                )

                for event in events:
                    try:
                        message = json.dumps(
                            {
                                "event_id": event.id,
                                "event_type": event.event_type,
                                "aggregate_type": event.aggregate_type,
                                "aggregate_id": event.aggregate_id,
                                "correlation_id": event.correlation_id,
                                "payload": event.payload,
                            }
                        )

                        with condition:
                            publish_state["tag"] = None
                            publish_state["returned"] = False

                        channel.basic_publish(
                            exchange=self.exchange,
                            routing_key=self.routing_key,
                            body=message,
                            properties=pika.BasicProperties(
                                delivery_mode=2,
                                content_type="application/json",
                            ),
                            mandatory=True,
                            on_publish=on_publish,
                        )

                        with condition:
                            confirmed = condition.wait_for(
                                lambda: (
                                    publish_state["tag"] is not None
                                    and (
                                        publish_state["tag"] in confirmed_tags
                                        or publish_state["tag"] in rejected_tags
                                    )
                                ),
                                timeout=self.CONFIRM_TIMEOUT_SECONDS,
                            )

                            if not confirmed:
                                raise TimeoutError(
                                    "Tempo esgotado aguardando confirmação "
                                    "do RabbitMQ."
                                )

                            delivery_tag = publish_state["tag"]

                            if delivery_tag in rejected_tags:
                                raise RuntimeError(
                                    "RabbitMQ rejeitou a publicação do evento."
                                )

                            if publish_state["returned"]:
                                raise RuntimeError(
                                    "RabbitMQ devolveu a mensagem: "
                                    "nenhuma fila recebeu o evento."
                                )

                            confirmed_tags.discard(delivery_tag)
                            rejected_tags.discard(delivery_tag)

                        logger.info(
                            "Evento confirmado pelo RabbitMQ",
                            extra={
                                "event_id": event.id,
                                "event_type": event.event_type,
                                "aggregate_id": event.aggregate_id,
                                "correlation_id": event.correlation_id,
                            },
                        )

                        repository.mark_as_published(event)
                        db.commit()

                        published_count += 1

                        logger.info(
                            "Evento marcado como publicado na Outbox",
                            extra={
                                "event_id": event.id,
                                "aggregate_id": event.aggregate_id,
                                "correlation_id": event.correlation_id,
                            },
                        )

                    except Exception:
                        db.rollback()

                        logger.exception(
                            "Falha ao publicar evento da Outbox",
                            extra={
                                "event_id": event.id,
                                "aggregate_id": event.aggregate_id,
                            },
                        )

                        raise

        except Exception:
            logger.exception(
                "Falha durante processamento da Outbox"
            )
            raise

        finally:
            self.rabbitmq.close()

            logger.info(
                "Publicação da Outbox encerrada",
                extra={
                    "published_count": published_count,
                },
            )

        return published_count
