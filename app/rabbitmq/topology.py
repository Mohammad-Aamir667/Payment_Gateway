import pika

EXCHANGE_NAME = "payment_events"
EXCHANGE_TYPE = "topic"

PROCESS_PAYMENT_QUEUE = "process_payment_queue"
PROCESS_PAYMENT_ROUTING_KEY = "payment.process"


def declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel):
    # 1. Declare exchange
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type=EXCHANGE_TYPE,
        durable=True,
    )

    # 2. Declare queue
    channel.queue_declare(
        queue=PROCESS_PAYMENT_QUEUE,
        durable=True,
    )

    # 3. Bind queue to exchange
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=PROCESS_PAYMENT_QUEUE,
        routing_key=PROCESS_PAYMENT_ROUTING_KEY,
    )