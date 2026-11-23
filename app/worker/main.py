import logging

from app.core.logging_config import configure_logging
from app.messaging.rabbitmq_consumer import RabbitMQConsumer


def main():
    configure_logging()

    logger = logging.getLogger(__name__)

    logger.info("Iniciando Orders Worker")

    consumer = RabbitMQConsumer()

    try:
        consumer.start()

    except Exception:
        logger.exception("Erro fatal na execução do Worker")
        raise

    finally:
        logger.info("Orders Worker finalizado")


if __name__ == "__main__":
    main()