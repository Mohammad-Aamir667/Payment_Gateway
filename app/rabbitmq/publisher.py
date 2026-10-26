
import json
from typing import Any

import pika

from app.rabbitmq.connection import create_connection
from app.rabbitmq.topology import EXCHANGE_NAME, declare_topology


def publish_message(
    routing_key: str,
    payload: dict[str, Any],
) -> None:
    connection = create_connection()

    try:
        channel = connection.channel()
        declare_topology(channel)

        channel.confirm_delivery()

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
            mandatory=True,
        )

    finally:
        connection.close()

