import json
from uuid import UUID

import pika

from app.rabbitmq.connection import create_connection
from app.rabbitmq.topology import (
    EXCHANGE_NAME,
    PROCESS_PAYMENT_ROUTING_KEY,
    declare_topology,
)


def publish_payment_processing(payment_id: UUID) -> None:

    connection = create_connection()

    try:
        channel = connection.channel()

        # Make sure exchange, queue and binding exist.
        declare_topology(channel)

        message = {
            "payment_id": str(payment_id),
        }

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=PROCESS_PAYMENT_ROUTING_KEY,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # persistent message
            ),
        )

    finally:
        connection.close()