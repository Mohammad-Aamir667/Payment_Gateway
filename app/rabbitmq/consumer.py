import json
from uuid import UUID

from app.payment.exceptions import ProviderCommunicationError
from app.rabbitmq.connection import create_connection
from app.rabbitmq.topology import (
    PROCESS_PAYMENT_QUEUE,
    declare_topology,
)
from app.workers.payment_worker import process_payment_job


def callback(channel, method, properties, body):

    try:
        message = json.loads(body)

        payment_id = UUID(message["payment_id"])

        print(
            f"Received payment processing job: {payment_id}"
        )
        process_payment_job(payment_id)
        
        # ACK only after the worker successfully completes.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )

        print(
            f"Payment processing job completed: {payment_id}"
        )

    except ProviderCommunicationError:

        print(
            "Provider communication failed. "
            "Requeueing message."
        )

        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )

    except Exception as exc:

        print(
            f"Unexpected worker error: {exc}"
        )

        # For now, don't endlessly redeliver malformed/
        # programming-error messages.
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )


def start_consumer():

    connection = create_connection()

    try:
        channel = connection.channel()

        # Ensure topology exists.
        declare_topology(channel)

        # Give one unacknowledged message to this consumer
        # at a time.
        channel.basic_qos(
            prefetch_count=1
        )

        channel.basic_consume(
            queue=PROCESS_PAYMENT_QUEUE,
            on_message_callback=callback,
            auto_ack=False,
        )

        print(
            f"Waiting for messages from "
            f"'{PROCESS_PAYMENT_QUEUE}'..."
        )

        channel.start_consuming()

    except KeyboardInterrupt:

        print("Stopping consumer...")

    finally:
        connection.close()


if __name__ == "__main__":
    start_consumer()