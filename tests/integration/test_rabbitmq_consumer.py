
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pika
import pytest

from app.messaging.rabbitmq_consumer import RabbitMQConsumer


def test_process_message_logs_correlation_id(caplog):
    consumer = RabbitMQConsumer()

    correlation_id = "123e4567-e89b-12d3-a456-426614174000"

    body = json.dumps(
        {
            "event_id": 1,
            "event_type": "ORDER_CREATED",
            "aggregate_type": "ORDER",
            "aggregate_id": 100,
            "correlation_id": correlation_id,
            "payload": {
                "order_id": 100,
            },
        }
    ).encode("utf-8")

    with caplog.at_level(
        logging.INFO,
        logger="app.messaging.rabbitmq_consumer",
    ):
        consumer.process_message(body)

    event_log = next(
        record
        for record in caplog.records
        if record.message == "Evento recebido"
    )

    assert event_log.correlation_id == correlation_id
    assert event_log.event_type == "ORDER_CREATED"
    assert event_log.aggregate_id == 100


def test_retry_count_without_retry_header():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    properties = SimpleNamespace(headers={})

    assert consumer._get_retry_count(properties) == 0


def test_retry_count_after_first_retry():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    properties = SimpleNamespace(
        headers={
            "x-retry-count": 1,
        }
    )

    assert consumer._get_retry_count(properties) == 1


def test_retry_count_after_second_retry():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    properties = SimpleNamespace(
        headers={
            "x-retry-count": 2,
        }
    )

    assert consumer._get_retry_count(properties) == 2


def test_retry_count_ignores_x_death():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    properties = SimpleNamespace(
        headers={
            "x-death": [
                {
                    "queue": "orders.retry",
                    "reason": "expired",
                    "count": 5,
                }
            ]
        }
    )

    assert consumer._get_retry_count(properties) == 0


def test_invalid_json_message_is_rejected():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    channel = Mock()
    method = Mock()
    method.delivery_tag = 123

    invalid_body = b"{invalid json"

    consumer.on_message(
        channel,
        method,
        None,
        invalid_body,
    )

    channel.basic_ack.assert_not_called()

    channel.basic_nack.assert_called_once_with(
        delivery_tag=123,
        requeue=False,
    )


def test_publish_retry_success(monkeypatch):
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    channel = Mock()
    connection = Mock()
    connection.connect.return_value = channel

    callbacks = {}

    def confirm_delivery(ack_nack_callback):
        callbacks["confirm"] = ack_nack_callback

    def basic_publish(**kwargs):
        kwargs["on_publish"](1)

        callbacks["confirm"](
            SimpleNamespace(
                method=pika.spec.Basic.Ack(),
            )
        )

    channel.confirm_delivery.side_effect = confirm_delivery
    channel.basic_publish.side_effect = basic_publish

    monkeypatch.setattr(
        "app.messaging.rabbitmq_consumer.RabbitMQConnection",
        lambda: connection,
    )

    properties = pika.BasicProperties(
        headers={"correlation_id": "123"},
        content_type="application/json",
    )

    body = b'{"order_id": 10}'

    consumer._publish_retry(properties, body)

    channel.basic_publish.assert_called_once()

    publish_args = channel.basic_publish.call_args.kwargs

    assert publish_args["exchange"] == "orders.retry.exchange"
    assert publish_args["routing_key"] == "orders.retry"
    assert publish_args["body"] == body
    assert publish_args["mandatory"] is True

    assert publish_args["properties"].headers == {
        "correlation_id": "123",
        "x-retry-count": 1,
    }

    assert publish_args["properties"].delivery_mode == 2
    assert publish_args["properties"].content_type == "application/json"

    connection.close.assert_called_once()


def test_publish_retry_preserves_previous_retry_count(monkeypatch):
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    channel = Mock()
    connection = Mock()
    connection.connect.return_value = channel

    callbacks = {}

    def confirm_delivery(ack_nack_callback):
        callbacks["confirm"] = ack_nack_callback

    def basic_publish(**kwargs):
        kwargs["on_publish"](1)

        callbacks["confirm"](
            SimpleNamespace(
                method=pika.spec.Basic.Ack(),
            )
        )

    channel.confirm_delivery.side_effect = confirm_delivery
    channel.basic_publish.side_effect = basic_publish

    monkeypatch.setattr(
        "app.messaging.rabbitmq_consumer.RabbitMQConnection",
        lambda: connection,
    )

    properties = pika.BasicProperties(
        headers={
            "correlation_id": "123",
            "x-retry-count": 1,
        },
        content_type="application/json",
    )

    consumer._publish_retry(
        properties,
        b'{"order_id": 10}',
    )

    publish_args = channel.basic_publish.call_args.kwargs

    assert publish_args["properties"].headers == {
        "correlation_id": "123",
        "x-retry-count": 2,
    }

    connection.close.assert_called_once()


def test_publish_retry_rejected(monkeypatch):
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    channel = Mock()
    connection = Mock()
    connection.connect.return_value = channel

    callbacks = {}

    def confirm_delivery(ack_nack_callback):
        callbacks["confirm"] = ack_nack_callback

    def basic_publish(**kwargs):
        kwargs["on_publish"](1)

        callbacks["confirm"](
            SimpleNamespace(
                method=pika.spec.Basic.Nack(),
            )
        )

    channel.confirm_delivery.side_effect = confirm_delivery
    channel.basic_publish.side_effect = basic_publish

    monkeypatch.setattr(
        "app.messaging.rabbitmq_consumer.RabbitMQConnection",
        lambda: connection,
    )

    properties = pika.BasicProperties(
        headers={},
        content_type="application/json",
    )

    body = b'{"order_id": 10}'

    with pytest.raises(RuntimeError, match="RabbitMQ rejeitou"):
        consumer._publish_retry(properties, body)

    connection.close.assert_called_once()


def test_publish_retry_timeout(monkeypatch):
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    channel = Mock()
    connection = Mock()
    connection.connect.return_value = channel

    channel.confirm_delivery.return_value = None

    channel.basic_publish.side_effect = (
        lambda **kwargs: kwargs["on_publish"](1)
    )

    monkeypatch.setattr(
        "app.messaging.rabbitmq_consumer.RabbitMQConnection",
        lambda: connection,
    )

    properties = pika.BasicProperties(
        headers={},
        content_type="application/json",
    )

    body = b'{"order_id": 10}'

    with pytest.raises(TimeoutError, match="Tempo esgotado"):
        consumer._publish_retry(properties, body)

    connection.close.assert_called_once()


def test_on_message_first_failure_sends_to_retry():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    consumer.process_message = Mock(
        side_effect=RuntimeError("Erro temporário")
    )

    consumer._publish_retry = Mock()

    channel = Mock()
    method = Mock()
    method.delivery_tag = 123

    properties = pika.BasicProperties(headers={})
    body = b'{"order_id": 10}'

    consumer.on_message(
        channel,
        method,
        properties,
        body,
    )

    consumer._publish_retry.assert_called_once_with(
        properties,
        body,
    )

    channel.basic_ack.assert_called_once_with(
        delivery_tag=123,
    )

    channel.basic_nack.assert_not_called()


def test_on_message_second_failure_sends_to_retry():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    consumer.process_message = Mock(
        side_effect=RuntimeError("Erro temporário")
    )

    consumer._publish_retry = Mock()

    channel = Mock()
    method = Mock()
    method.delivery_tag = 456

    properties = pika.BasicProperties(
        headers={
            "x-retry-count": 1,
        }
    )

    body = b'{"order_id": 10}'

    consumer.on_message(
        channel,
        method,
        properties,
        body,
    )

    consumer._publish_retry.assert_called_once_with(
        properties,
        body,
    )

    channel.basic_ack.assert_called_once_with(
        delivery_tag=456,
    )

    channel.basic_nack.assert_not_called()


def test_on_message_third_failure_sends_to_dlq():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    consumer.process_message = Mock(
        side_effect=RuntimeError("Erro temporário")
    )

    consumer._publish_retry = Mock()

    channel = Mock()
    method = Mock()
    method.delivery_tag = 789

    properties = pika.BasicProperties(
        headers={
            "x-retry-count": 2,
        }
    )

    body = b'{"order_id": 10}'

    consumer.on_message(
        channel,
        method,
        properties,
        body,
    )

    consumer._publish_retry.assert_not_called()

    channel.basic_ack.assert_not_called()

    channel.basic_nack.assert_called_once_with(
        delivery_tag=789,
        requeue=False,
    )


def test_on_message_retry_publish_failure_requeues_message():
    consumer = RabbitMQConsumer(
        rabbitmq_connection=Mock(),
    )

    consumer.process_message = Mock(
        side_effect=RuntimeError("Erro temporário")
    )

    consumer._publish_retry = Mock(
        side_effect=RuntimeError("Falha na publicação")
    )

    channel = Mock()
    method = Mock()
    method.delivery_tag = 999

    properties = pika.BasicProperties(headers={})
    body = b'{"order_id": 10}'

    consumer.on_message(
        channel,
        method,
        properties,
        body,
    )

    consumer._publish_retry.assert_called_once()

    channel.basic_ack.assert_not_called()

    channel.basic_nack.assert_called_once_with(
        delivery_tag=999,
        requeue=True,
    )



def test_consumer_start_starts_consuming(monkeypatch):
    rabbitmq = Mock()
    channel = Mock()

    rabbitmq.connect.return_value = channel

    consumer = RabbitMQConsumer(
        rabbitmq_connection=rabbitmq,
    )

    monkeypatch.setattr(
        consumer.stop_event,
        "wait",
        lambda: None,
    )

    consumer.start()

    channel.basic_qos.assert_called_once_with(
        prefetch_count=1,
    )

    channel.basic_consume.assert_called_once_with(
        queue="orders.events",
        on_message_callback=consumer.on_message,
        auto_ack=False,
    )

    rabbitmq.close.assert_called_once()



def test_consumer_close_stops_consuming():
    from unittest.mock import Mock

    rabbitmq = Mock()
    rabbitmq.connection = Mock()

    consumer = RabbitMQConsumer(
        rabbitmq_connection=rabbitmq,
    )

    consumer.close()

    assert consumer.stop_event.is_set()
    rabbitmq.close.assert_called_once()
