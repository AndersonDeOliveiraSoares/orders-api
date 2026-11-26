
import os

import pika
from dotenv import load_dotenv


load_dotenv()


class RabbitMQConnection:

    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
    ):
        self.host = host or os.getenv(
            "RABBITMQ_HOST",
            "localhost",
        )

        self.port = int(
            port if port is not None
            else os.getenv("RABBITMQ_PORT", "5672")
        )

        self.username = username or os.getenv(
            "RABBITMQ_USER",
            "guest",
        )

        self.password = password or os.getenv(
            "RABBITMQ_PASSWORD",
            "guest",
        )

        self.connection = None
        self.channel = None

    def connect(self):
        credentials = pika.PlainCredentials(
            self.username,
            self.password,
        )

        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )

        self.connection = pika.Connection(parameters)
        self.channel = self.connection.channel()

        return self.channel

    def close(self):
        if self.connection:
            self.connection.close()
            self.channel = None
            self.connection = None
