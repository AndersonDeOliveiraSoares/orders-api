
import json
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from app.messaging.rabbitmq_connection import RabbitMQConnection
from app.models.models_outbox import OutboxEvent
from app.services.service_outbox_publisher import OutboxPublisher
from tests.conftest import test_engine


def test_outbox_event_is_published_to_rabbitmq():
    session_factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
    )

    unique_id = uuid4().hex
    correlation_id = str(uuid4())
    aggregate_id = uuid4().int % 1_000_000_000 + 1

    exchange_name = f"test.orders.{unique_id}"
    queue_name = f"test.orders.events.{unique_id}"
    routing_key = f"test.order.created.{unique_id}"

    event_id = None
    rabbitmq = RabbitMQConnection()

    try:
        # Cria um evento isolado no banco de testes.
        with session_factory() as db:
            event = OutboxEvent(
                event_type="ORDER_CREATED",
                aggregate_type="ORDER",
                aggregate_id=aggregate_id,
                correlation_id=correlation_id,
                payload={
                    "order_id": aggregate_id,
                    "customer_id": 1,
                },
            )

            db.add(event)
            db.commit()
            db.refresh(event)

            event_id = event.id

        # Conecta ao RabbitMQ para consumir a mensagem.
        channel = rabbitmq.connect()

        # Declara o exchange com os mesmos parâmetros
        # utilizados pelo OutboxPublisher.
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type="direct",
            durable=True,
            auto_delete=False,
        )

        # Declara a fila com os mesmos parâmetros
        # utilizados pelo OutboxPublisher.
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            exclusive=False,
            auto_delete=False,
        )

        # Vincula a fila ao exchange.
        channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key,
        )

        # Publica somente o evento criado neste teste.
        publisher = OutboxPublisher(
            session_factory=session_factory,
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key,
        )

        published_count = publisher.publish_pending_events(
            event_ids=[event_id],
        )

        assert published_count == 1

        # Consome a mensagem publicada.
        method, properties, body = channel.basic_get(
            queue=queue_name,
            auto_ack=True,
        )

        assert method is not None
        assert properties.content_type == "application/json"

        message = json.loads(body)

        assert message["event_id"] == event_id
        assert message["event_type"] == "ORDER_CREATED"
        assert message["aggregate_type"] == "ORDER"
        assert message["aggregate_id"] == aggregate_id
        assert message["correlation_id"] == correlation_id
        assert message["payload"]["order_id"] == aggregate_id

        # Confirma a atualização do evento no PostgreSQL.
        with session_factory() as db:
            published_event = db.get(OutboxEvent, event_id)

            assert published_event is not None
            assert published_event.status == "PUBLISHED"
            assert published_event.published_at is not None

    finally:
        # Remove a fila e o exchange de teste.
        if rabbitmq.channel and rabbitmq.channel.is_open:
            rabbitmq.channel.queue_delete(queue=queue_name)
            rabbitmq.channel.exchange_delete(exchange=exchange_name)

        rabbitmq.close()

        # Remove o evento criado pelo teste.
        if event_id is not None:
            with session_factory() as db:
                event = db.get(OutboxEvent, event_id)

                if event is not None:
                    db.delete(event)
                    db.commit()
