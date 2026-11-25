
import logging
import threading

from app.core.logging_config import configure_logging
from app.messaging.rabbitmq_consumer import RabbitMQConsumer
from app.services.service_outbox_publisher import OutboxPublisher


logger = logging.getLogger(__name__)

OUTBOX_PUBLISH_INTERVAL_SECONDS = 5
OUTBOX_BATCH_SIZE = 100


def publish_outbox_periodically(stop_event: threading.Event):
    publisher = OutboxPublisher()

    logger.info("Outbox Publisher iniciado")

    while not stop_event.is_set():
        try:
            published_count = publisher.publish_pending_events(
                limit=OUTBOX_BATCH_SIZE
            )

            if published_count:
                logger.info(
                    "Lote de eventos publicado",
                    extra={"published_count": published_count},
                )

        except Exception:
            logger.exception(
                "Erro na execução periódica do Outbox Publisher"
            )

        stop_event.wait(OUTBOX_PUBLISH_INTERVAL_SECONDS)

    logger.info("Outbox Publisher encerrado")


def main():
    configure_logging()

    logger.info("Iniciando Orders Worker")

    stop_event = threading.Event()

    publisher_thread = threading.Thread(
        target=publish_outbox_periodically,
        args=(stop_event,),
        name="outbox-publisher",
        daemon=True,
    )

    consumer = RabbitMQConsumer()

    publisher_thread.start()

    try:
        consumer.start()

    except Exception:
        logger.exception("Erro fatal na execução do Worker")
        raise

    finally:
        stop_event.set()
        publisher_thread.join(timeout=10)

        logger.info("Orders Worker finalizado")


if __name__ == "__main__":
    main()
