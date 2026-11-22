
import pika


class RabbitMQConnection:

    def __init__(
        self,
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

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
        if self.channel and self.channel.is_open:
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()
