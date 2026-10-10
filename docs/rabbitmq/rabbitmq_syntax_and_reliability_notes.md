# RabbitMQ Syntax and Reliability Notes

Practical notes for the payment gateway project: the Pika syntax we
discussed, what the terms mean, failure scenarios, and interview
questions.

## 1. Message flow

``` text
Payment API -> PostgreSQL: create Payment(PROCESSING), history, idempotency record
Payment API -> RabbitMQ exchange: payment_events
Exchange -> process_payment_queue (routing key: payment.process)
Queue -> worker -> PSP
Worker -> PostgreSQL: reconcile and persist payment status
```

RabbitMQ transports jobs. It does not decide whether a payment
succeeded. A consumer ACK means that delivery was handled according to
the consumer's policy; it does not mean the payment succeeded.

## 2. Connection setup

``` python
# app/rabbitmq/connection.py
import pika

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = "guest"
RABBITMQ_PASSWORD = "guest"

def create_connection():
    credentials = pika.PlainCredentials(
        RABBITMQ_USERNAME,
        RABBITMQ_PASSWORD,
    )
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(parameters)
```

-   `BlockingConnection`: synchronous Pika API.
-   `heartbeat=60`: requests a heartbeat interval to help detect an
    unresponsive connection; the negotiated interval is used.
-   `blocked_connection_timeout=300`: raises a timeout if the broker
    signals that the connection is blocked and it remains blocked for
    that period. It is not a general timeout for every operation.
-   `guest/guest` is for local development, not a production credential
    recommendation.

Pika has other adapters, including `SelectConnection` and
`AsyncioConnection`.

## 3. Exchange, queue, and binding

Project topology:

``` text
payment_events (topic exchange, durable)
       |
       | routing key: payment.process
       v
process_payment_queue (durable)
```

``` python
# app/rabbitmq/topology.py
import pika

EXCHANGE_NAME = "payment_events"
EXCHANGE_TYPE = "topic"
PROCESS_PAYMENT_QUEUE = "process_payment_queue"
PROCESS_PAYMENT_ROUTING_KEY = "payment.process"

def declare_topology(
    channel: pika.adapters.blocking_connection.BlockingChannel,
):
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type=EXCHANGE_TYPE,
        durable=True,
    )
    channel.queue_declare(
        queue=PROCESS_PAYMENT_QUEUE,
        durable=True,
    )
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=PROCESS_PAYMENT_QUEUE,
        routing_key=PROCESS_PAYMENT_ROUTING_KEY,
    )
```

-   **Exchange:** receives published messages and routes them.
-   **Queue:** stores messages for consumers.
-   **Binding:** connects an exchange to a queue using a routing rule.
-   **Routing key:** a string used for routing.
-   **Topic exchange:** supports patterns such as `payment.*`.
-   Declaring existing resources with matching settings is safe to
    repeat. Incompatible declarations can cause a channel error.
-   Publisher and consumer startup can both call `declare_topology()`,
    so the app need not depend on manual setup in the management UI.

## 4. Publisher syntax

``` python
import json
import pika

channel.basic_publish(
    exchange=EXCHANGE_NAME,
    routing_key=PROCESS_PAYMENT_ROUTING_KEY,
    body=json.dumps({
        "event_type": "payment.process",
        "payment_id": payment_id,
    }),
    properties=pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
    ),
)
```

-   `exchange`: exchange receiving the message.
-   `routing_key`: key used to route it.
-   `body`: message content. Here the dictionary is JSON-encoded.
-   `content_type="application/json"`: metadata describing the body; it
    does not validate or serialize it.
-   `delivery_mode=2`: requests a persistent message.

**Durable queue and persistent message are separate.** A durable queue
is intended to survive a broker restart; `delivery_mode=2` requests
message persistence. Neither setting alone guarantees survival of every
infrastructure failure or proves that a particular publish was accepted.

### What does `basic_publish()` prove?

Without publisher confirms, a successful call does not provide strong
application-visible proof that RabbitMQ accepted responsibility for the
message. If the network breaks, the broker may not have received it---or
it may have received it while the publisher lost the connection. The
publisher can be uncertain.

## 5. Publisher confirms

With Pika's blocking channel, enable confirm mode using:

``` python
channel.confirm_delivery()
```

Then publish:

``` python
channel.basic_publish(
    exchange=EXCHANGE_NAME,
    routing_key=PROCESS_PAYMENT_ROUTING_KEY,
    body=json.dumps(message),
    properties=pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
    ),
)
```

In real code, handle confirm failures, unroutable-message behavior, and
connection exceptions according to the installed Pika version.

Publisher confirms answer: **did RabbitMQ confirm this publication?**
They do not mean that a consumer received it, a worker processed it, a
payment succeeded, or a merchant webhook was delivered.

If the broker accepts a message but the connection fails before the
publisher learns the result, publication is uncertain. Retrying can
produce a duplicate. Consumers must still be idempotent. Also handle
unroutable messages appropriately; a confirm should not be treated as
proof that the message reached the intended queue in every topology.

## 6. Consumer setup and callback

``` python
connection = create_connection()
channel = connection.channel()
declare_topology(channel)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(
    queue=PROCESS_PAYMENT_QUEUE,
    on_message_callback=callback,
    auto_ack=False,
)
channel.start_consuming()
```

-   `basic_qos(prefetch_count=1)`: limits this consumer to one
    unacknowledged delivery at a time under this configuration. It does
    not mean only one worker process can exist.
-   `auto_ack=False`: use manual acknowledgements.
-   `basic_consume`: registers a callback.
-   `start_consuming`: starts the blocking consumption loop.
-   The consumer should be a separate long-running process, not a
    FastAPI request handler.

Pika calls the callback with:

``` python
def callback(channel, method, properties, body):
    ...
```

-   `channel`: channel used to ACK/NACK.
-   `method`: delivery metadata; `method.delivery_tag` identifies this
    delivery on this channel.
-   `properties`: metadata such as content type and delivery mode.
-   `body`: message bytes, which must be parsed and validated.

### ACK and NACK

``` python
channel.basic_ack(delivery_tag=method.delivery_tag)
```

Acknowledges that delivery as handled.

``` python
channel.basic_nack(
    delivery_tag=method.delivery_tag,
    requeue=True,
)
```

Rejects the delivery and requests requeueing. Endless immediate
requeueing can create a hot loop; a retry policy needs bounded attempts
and backoff.

`delivery_tag` is not the payment ID or a globally unique message ID. It
is scoped to the channel.

ACK/NACK are one-way instructions: the consumer does not receive a
separate acknowledgement that RabbitMQ processed its ACK/NACK.

## 7. ACK/NACK uncertainty

Scenario:

1.  RabbitMQ delivers a job.
2.  Worker commits `SUCCESS` to PostgreSQL.
3.  Worker sends ACK.
4.  Connection fails before the worker knows whether RabbitMQ received
    the ACK.

RabbitMQ may have received the ACK and removed the message. Or the
delivery may remain unacknowledged and be requeued/redelivered when the
connection closes. The worker cannot safely assume which outcome
happened. Do not retry an ACK on a stale channel; reconnect and safely
handle possible redelivery.

The payment worker must be idempotent:

-   If the payment is already terminal (`SUCCESS` or `FAILED`), return
    without processing it again.
-   If `provider_payment_id` is known, retrieve provider status.
-   Otherwise, look up the provider payment by the gateway payment ID.
-   If found, use the result.
-   Initiate a provider payment only if recovery lookup says no provider
    payment exists.

**Never create when you can recover.** A local `PROCESSING` status does
not prove that the PSP was never called; the worker could have crashed
after the PSP created a transaction but before the gateway saved the
provider ID.

## 8. What if RabbitMQ is unavailable?

Failure sequence:

1.  The API commits `Payment`, `PaymentHistory`, and `IdempotencyKey` to
    PostgreSQL.
2.  RabbitMQ is unavailable when the API tries to publish.
3.  The payment exists, but the processing job may not exist in
    RabbitMQ.

Idempotency prevents a repeated merchant request from creating a
duplicate payment, but it does not by itself publish the missing job.

Possible design elements:

-   **Transactional outbox:** write an outbox event in the same
    PostgreSQL transaction as the payment.
-   **Separate publisher:** reads pending outbox events and publishes
    them later.
-   **Publisher confirms:** helps distinguish confirmed publication from
    failure or uncertainty.
-   **Scheduled recovery/reconciliation:** can inspect pending outbox
    events or eligible stuck payments. It complements a durable design;
    it is not a substitute for one.
-   **Merchant-facing contract:** decide whether the API can acknowledge
    a durably created payment as `PROCESSING` or should return a
    service-unavailable response. If the database already committed, do
    not imply that no payment was created. The correct response depends
    on the API contract.

## 9. Transactional outbox

Without an outbox:

``` text
Commit payment to PostgreSQL
          |
          v
Publish job to RabbitMQ
```

If the process crashes between these steps, the payment may exist
without a queued job.

With an outbox:

``` text
One PostgreSQL transaction:
  - Payment(PROCESSING)
  - initial PaymentHistory
  - IdempotencyKey
  - OutboxEvent
             |
           COMMIT
             |
Outbox publisher reads pending event
             |
Publish to RabbitMQ with confirms
             |
Mark event as published
```

The payment and intention to publish are committed atomically. If
RabbitMQ is unavailable, the outbox event remains pending.

The outbox does not guarantee exactly-once delivery. RabbitMQ may accept
the message, then the publisher may crash before marking the outbox row
published. Recovery can publish it again, so consumers still need
idempotency.

## 10. Broker crash and message durability

Durable queues plus persistent messages help across ordinary broker
restarts, but do not cover every infrastructure failure.

Consider: - Is the queue durable? - Was the message published with
`delivery_mode=2`? - Did the publisher receive a confirm? - Was the
message routed to the intended queue? - Is RabbitMQ a single node or
using replicated queues? - Can the consumer safely handle redelivery?

Replicated queue types such as quorum queues can improve resilience to
an individual node failure, subject to their configuration and
availability trade-offs. They do not remove the need for publisher
confirms, idempotency, and recovery logic.

## 11. Retry, discard, and dead-letter queue (DLQ)

A worker can conceptually return:

``` python
class PaymentJobResult(Enum):
    COMPLETED = "completed"
    RETRY = "retry"
    DISCARD = "discard"
```

Policy mapping:

-   `COMPLETED` → ACK.
-   `RETRY` → retry according to policy; a simple implementation might
    NACK with `requeue=True`.
-   `DISCARD` → ACK/remove from the active queue under the current
    learning-project policy, after logging and recording useful details.

A production-minded policy should add bounded attempts, backoff, a DLQ
for poison/exhausted messages, and monitoring/replay procedures. The
current project intentionally defers the full retry/DLQ mechanism.

Do not classify every exception as retryable: - Temporary database
connectivity problems may be retryable. - Invalid payloads or missing
required records may be non-retryable. - A PSP timeout is **uncertain**,
not proof of payment failure. Query/reconcile with the PSP before
initiating again.

## 12. Why not promise exactly-once execution?

PostgreSQL, RabbitMQ, a worker, and the PSP do not share one transaction
covering every side effect. A process can perform an external action and
crash before recording it. A publisher can lose a confirmation; a
consumer can lose its ACK.

The practical approach is: - durable intent; - at-least-once delivery; -
idempotent consumers; - PSP idempotency/recovery; - reconciliation; -
bounded retries, DLQ, and monitoring.

This can produce effectively-once **business behavior** through
idempotency and recovery, but it is not a promise that every message or
function runs exactly once.

## 13. Reusing these concepts for merchant webhooks

A topic exchange can route different event types to separate queues:

``` text
payment_events (topic exchange)
   |                         |
   | payment.process         | webhook.deliver
   v                         v
process_payment_queue    webhook_delivery_queue
```

Webhook failure scenarios: - merchant endpoint is down or times out; -
merchant processes the event but the sender loses the HTTP response; -
retry creates duplicate delivery; - sender crashes before recording
success.

Use stable event IDs, delivery records, bounded retries/backoff, and
inspection/replay tooling. Merchants should be able to deduplicate
events. Do not blindly apply payment-initiation retry rules to webhooks:
retrying a notification and retrying a financial side effect have
different risks.

## 14. Interview questions

1.  Why use a queue instead of processing payment inside the API
    request?
2.  What does `auto_ack=False` change?
3.  What does `delivery_tag` identify?
4.  Does ACK mean the payment succeeded?
5.  What if the worker commits `SUCCESS` and crashes before ACK?
6.  What if RabbitMQ accepts a publish but the publisher loses the
    connection before confirmation?
7.  What do publisher confirms guarantee---and what do they not
    guarantee?
8.  Why do durable queues and persistent messages matter? Are they
    enough?
9.  What if PostgreSQL commits a payment but RabbitMQ is unavailable?
10. How does the transactional outbox close the dual-write gap?
11. Can an outbox publisher publish the same event more than once?
12. Why are consumers still idempotent when confirms are enabled?
13. Why is a PSP timeout not equivalent to a failed payment?
14. Why look up the PSP by gateway payment ID before creating a new
    provider payment?
15. Why use bounded retries and a DLQ instead of endless immediate
    requeueing?
16. How do webhook retries differ from payment initiation retries?
17. How would you choose between returning `503` and acknowledging a
    durably created payment as `PROCESSING`?

A strong answer identifies the failure, says which system state is known
or uncertain, explains recovery, and states the limits of the guarantee.

## 15. Suggested implementation order

1.  Finish the basic publisher and consumer.
2.  Implement transactional outbox.
3.  Add bounded retries, backoff, and DLQ.
4.  Add PSP callbacks/status confirmation and reconciliation.
5.  Test duplicate delivery, connection loss, uncertain publication, and
    recovery.
6.  Build merchant webhooks using durable events, delivery tracking,
    idempotency, and retries.

Defer multi-node broker operations and recovery from process/OS/server
failure until core application-level reliability is tested.

## Quick syntax reference

  ----------------------------------------------------------------------------------
  Syntax / setting                               Meaning
  ---------------------------------------------- -----------------------------------
  `BlockingConnection(...)`                      Create a synchronous Pika
                                                 connection

  `connection.channel()`                         Open a channel

  `exchange_declare(...)`                        Declare an exchange

  `queue_declare(..., durable=True)`             Declare a durable queue

  `queue_bind(...)`                              Bind queue to exchange/routing key

  `basic_publish(...)`                           Publish a message

  `delivery_mode=2`                              Request a persistent message

  `content_type="application/json"`              Describe body format

  `confirm_delivery()`                           Enable publisher confirms for
                                                 Pika's blocking channel

  `basic_qos(prefetch_count=1)`                  Limit unacknowledged deliveries
                                                 under configured QoS

  `basic_consume(..., auto_ack=False)`           Consume with manual ACK/NACK

  `start_consuming()`                            Run consumer loop

  `basic_ack(delivery_tag=...)`                  Acknowledge a delivery

  `basic_nack(delivery_tag=..., requeue=True)`   Reject and request requeue

  Transactional outbox                           Atomically persist business state
                                                 and publication intent

  Publisher confirm                              Broker confirmation, not consumer
                                                 processing

  Idempotent consumer                            Makes repeated delivery safe

  DLQ                                            Queue for messages routed aside by
                                                 dead-letter policy
  ----------------------------------------------------------------------------------
