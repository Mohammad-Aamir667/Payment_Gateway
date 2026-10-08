import json
from uuid import UUID

from app.payment.exceptions import ProviderCommunicationError
from app.rabbitmq.connection import create_connection
from app.rabbitmq.topology import (
    PROCESS_PAYMENT_QUEUE,
    declare_topology,
)
from app.workers.payment_worker import PaymentJobResult, process_payment_job


def callback(channel, method, properties, body):

    payment_id = None

    try:
        message = json.loads(body)

        payment_id = UUID(message["payment_id"])

        print(
            f"Received payment processing job: {payment_id}"
        )

        result = process_payment_job(payment_id)

        if result == PaymentJobResult.COMPLETED:

            channel.basic_ack(
                delivery_tag=method.delivery_tag
            )

            print(
                f"ACK: payment job completed: {payment_id}"
            )

        elif result == PaymentJobResult.RETRY:

            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True,
            )

            print(
                f"REQUEUE: payment job will be retried: {payment_id}"
            )

        elif result == PaymentJobResult.DISCARD:

            channel.basic_ack(
                delivery_tag=method.delivery_tag
            )

            print(
                f"DISCARD: payment job is not retryable: {payment_id}"
            )
    except Exception as exc:

        print(
            f"Unexpected consumer error for payment "
            f"{payment_id}: {exc}"
        )

        # Temporary policy:
        # don't let an unexpected exception kill the consumer.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
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

    except Exception as exc:
        print(
            f"Consumer failed: {exc}"
        )

    finally:
        if connection is not None and connection.is_open:
            connection.close()
            
if __name__ == "__main__":
    start_consumer()