
import json
import threading

import pika

from app.messaging.rabbitmq_connection import RabbitMQConnection


class RabbitMQConsumer:

    def __init__(
        self,
        rabbitmq_connection=None,
        exchange="orders",
        queue="orders.events",
        routing_key="order.created",
    ):
        self.rabbitmq = rabbitmq_connection or RabbitMQConnection()

        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key

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

    def process_message(self, body: bytes):
        message = json.loads(body)

        print("Evento recebido:")
        print(
            json.dumps(
                message,
                indent=4,
                ensure_ascii=False,
            )
        )

    def on_message(self, channel, method, properties, body):
        try:
            self.process_message(body)

        except json.JSONDecodeError as exc:
            print(f"Mensagem JSON inválida: {exc}")

            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )

            print("Mensagem inválida encaminhada para DLQ.")
            return

        except Exception as exc:
            print(f"Erro ao processar mensagem: {exc}")

            retry_count = self._get_retry_count(properties)

            if retry_count < 2:
                try:
                    self._publish_retry(properties, body)

                    channel.basic_ack(
                        delivery_tag=method.delivery_tag,
                    )

                    print(
                        f"Mensagem encaminhada para Retry "
                        f"{retry_count + 1}/2."
                    )

                except Exception as retry_exc:
                    print(
                        f"Erro ao publicar mensagem no Retry: "
                        f"{retry_exc}"
                    )

                    channel.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True,
                    )

                    print(
                        "Mensagem devolvida à fila para nova tentativa."
                    )

            else:
                channel.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=False,
                )

                print("Limite de tentativas atingido. Mensagem enviada à DLQ.")

            return

        channel.basic_ack(
            delivery_tag=method.delivery_tag,
        )

        print("Mensagem confirmada (ACK).")

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

            headers = dict(properties.headers or {})

            channel.basic_publish(
                exchange="orders.retry.exchange",
                routing_key="orders.retry",
                body=body,
                properties=pika.BasicProperties(
                    headers=headers,
                    delivery_mode=2,
                    content_type=(
                        properties.content_type or "application/json"
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

        finally:
            connection.close()

    def start(self):
        self.stop_event.clear()

        self.connect()

        self.channel.basic_qos(
            prefetch_count=1,
        )

        self.channel.basic_consume(
            queue=self.queue,
            on_message_callback=self.on_message,
            auto_ack=False,
        )

        print(f"Consumindo fila: {self.queue}")
        print("Aguardando mensagens... Pressione Ctrl+C para sair.")

        try:
            self.stop_event.wait()

        except KeyboardInterrupt:
            print("\nEncerrando consumidor...")

        finally:
            self.close()

    def close(self):
        self.stop_event.set()
        self.rabbitmq.close()
        print("Consumidor encerrado.")

    def _get_retry_count(self, properties) -> int:
        if properties is None:
            return 0

        headers = properties.headers or {}
        deaths = headers.get("x-death", [])

        for death in deaths:
            if (
                death.get("queue") == "orders.retry"
                and death.get("reason") == "expired"
            ):
                return death.get("count", 0)

        return 0
