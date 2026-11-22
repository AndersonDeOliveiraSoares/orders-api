
import time
from uuid import uuid4

import pika

from app.messaging.rabbitmq_connection import RabbitMQConnection


def wait_for_message(channel, queue, timeout=45):
    """Aguarda uma mensagem aparecer na fila."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(
            queue=queue,
            auto_ack=False,
        )

        if method is not None:
            return method, properties, body

        time.sleep(0.5)

    raise TimeoutError(
        f"Nenhuma mensagem recebida na fila {queue}."
    )


def get_retry_count(properties, retry_queue):
    """Obtém a quantidade de expirações registrada pelo RabbitMQ."""
    headers = properties.headers or {}

    for death in headers.get("x-death", []):
        if (
            death.get("queue") == retry_queue
            and death.get("reason") == "expired"
        ):
            return death.get("count", 0)

    return 0


def test_rabbitmq_retry_and_dlq_real():
    rabbitmq = RabbitMQConnection()
    channel = None

    unique_id = uuid4().hex

    main_exchange = f"test.retry.main.{unique_id}"
    retry_exchange = f"test.retry.exchange.{unique_id}"
    dlx_exchange = f"test.retry.dlx.{unique_id}"

    main_queue = f"test.retry.main.queue.{unique_id}"
    retry_queue = f"test.retry.retry.queue.{unique_id}"
    dlq_queue = f"test.retry.dlq.{unique_id}"

    routing_key = "message.created"
    retry_routing_key = "message.retry"
    dlq_routing_key = "message.dead"

    body = b'{"test_id": "' + unique_id.encode() + b'"}'

    try:
        channel = rabbitmq.connect()

        # Exchanges isolados para este teste.
        for exchange in (
            main_exchange,
            retry_exchange,
            dlx_exchange,
        ):
            channel.exchange_declare(
                exchange=exchange,
                exchange_type="direct",
                durable=True,
            )

        # Fila principal: rejeições vão para a DLQ.
        channel.queue_declare(
            queue=main_queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": dlx_exchange,
                "x-dead-letter-routing-key": dlq_routing_key,
            },
        )

        # Fila Retry: expira após 30 segundos e retorna à principal.
        channel.queue_declare(
            queue=retry_queue,
            durable=True,
            arguments={
                "x-message-ttl": 30000,
                "x-dead-letter-exchange": main_exchange,
                "x-dead-letter-routing-key": routing_key,
            },
        )

        # Fila de mensagens rejeitadas.
        channel.queue_declare(
            queue=dlq_queue,
            durable=True,
        )

        channel.queue_bind(
            exchange=main_exchange,
            queue=main_queue,
            routing_key=routing_key,
        )

        channel.queue_bind(
            exchange=retry_exchange,
            queue=retry_queue,
            routing_key=retry_routing_key,
        )

        channel.queue_bind(
            exchange=dlx_exchange,
            queue=dlq_queue,
            routing_key=dlq_routing_key,
        )

        # Publica uma mensagem exclusiva.
        channel.basic_publish(
            exchange=main_exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers={"test_id": unique_id},
            ),
            mandatory=True,
        )

        # Recupera a mensagem da fila principal.
        current = wait_for_message(channel, main_queue)

        # Simula duas falhas temporárias e duas passagens pelo Retry.
        for attempt in range(1, 3):
            method, properties, received_body = current

            assert received_body == body

            assert get_retry_count(
                properties,
                retry_queue,
            ) == attempt - 1

            # Republica no Retry preservando os headers.
            channel.basic_publish(
                exchange=retry_exchange,
                routing_key=retry_routing_key,
                body=received_body,
                properties=properties,
                mandatory=True,
            )

            # Confirma a mensagem original somente após publicar o Retry.
            channel.basic_ack(
                delivery_tag=method.delivery_tag,
            )

            # Aguarda o TTL e o retorno à fila principal.
            current = wait_for_message(
                channel,
                main_queue,
                timeout=45,
            )

        # Terceira falha: deve encaminhar diretamente à DLQ.
        method, properties, received_body = current

        assert received_body == body

        # assert get_retry_count(
        #     properties,
        #     retry_queue,
        # ) == 2
        print("\nHeaders recebidos na terceira tentativa:")
        print(properties.headers)

        print("\nContagem de Retry:")
        print(get_retry_count(properties, retry_queue))

        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )

        # Confirma que a mensagem chegou à DLQ.
        dlq_message = wait_for_message(
            channel,
            dlq_queue,
            timeout=10,
        )

        dlq_method, dlq_properties, dlq_body = dlq_message

        assert dlq_body == body
        assert dlq_properties.headers["test_id"] == unique_id

        # Confirma o consumo da mensagem da DLQ de teste.
        channel.basic_ack(
            delivery_tag=dlq_method.delivery_tag,
        )

    finally:
        if channel and channel.is_open:
            for queue in (
                main_queue,
                retry_queue,
                dlq_queue,
            ):
                channel.queue_delete(queue=queue)

            for exchange in (
                main_exchange,
                retry_exchange,
                dlx_exchange,
            ):
                channel.exchange_delete(exchange=exchange)

        rabbitmq.close()
