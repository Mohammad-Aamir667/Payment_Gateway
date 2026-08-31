RabbitMQ and Asynchronous Payment Processing

Purpose

This document captures the reasoning, concepts, experiments, and design decisions discussed while introducing RabbitMQ into the payment gateway.

The goal is not just to document RabbitMQ syntax, but to explain why a message queue is needed for payment processing, what reliability problems it solves, what new problems it introduces, and how those problems connect to the payment gateway's existing reliability design.

1. Why We Need Asynchronous Payment Processing

The payment creation API has an important responsibility boundary:

Merchant
   ↓
POST /payments
   ↓
Validate request
   ↓
BEGIN TRANSACTION
   ↓
Create Payment(PROCESSING)
Create PaymentHistory
Create IdempotencyKey
   ↓
COMMIT
   ↓
201 Created

The payment has now been durably accepted by the gateway.

The gateway should then process that payment with the external Payment Service Provider (PSP).

A PSP is an independent external system and can be:

slow,

temporarily unavailable,

affected by network timeouts,

uncertain about whether a request was processed.

Therefore, payment creation should not depend on a long-running PSP call.

The desired separation is:

Payment Creation
      ↓
COMMIT
      ↓
Return 201 PROCESSING

independently

Payment Processing
      ↓
PSP
      ↓
SUCCESS / FAILED / uncertain

The merchant therefore receives an acknowledgement that the payment attempt was accepted, while final payment status is determined later.

2. Why a Background Worker Is Needed

Without a worker/queue, the API could do this:

POST /payments
   ↓
Create payment
   ↓
Call PSP
   ↓
Wait for PSP
   ↓
Update payment
   ↓
Return response

This couples the merchant's HTTP request to the availability and latency of the PSP.

A slow PSP can make the merchant request slow. A PSP timeout can leave the HTTP request waiting while the gateway still does not know whether the payment succeeded.

A worker separates these responsibilities:

HTTP API
   ↓
Durably create payment
   ↓
Queue processing work
   ↓
Return response

Worker
   ↓
Take processing job
   ↓
Call PSP
   ↓
Update payment state

The queue therefore represents a durable handoff of work.

The API says:

Process payment pay_123.

The worker later performs that work.

3. What Is a Message Queue?

At a high level:

Producer
   ↓
Queue
   ↓
Consumer / Worker

The producer creates work.

The queue holds the work until a consumer processes it.

The consumer takes the work and performs it.

For the payment gateway:

Payment API
   ↓
"Process payment pay_123"
   ↓
Message Queue
   ↓
Payment Worker
   ↓
process_payment(pay_123)

The queue allows the producer and consumer to operate independently in time.

4. Why RabbitMQ?

RabbitMQ is a message broker designed around messaging, routing, queues, consumers, and acknowledgements.

For this payment gateway, the immediate problem is naturally expressed as:

This payment needs to be processed as a unit of work.

RabbitMQ is a strong fit for this work-queue model.

Why not Redis?

Redis can be used to implement queue-like systems, but Redis is fundamentally a data store with additional messaging/data-structure capabilities.

RabbitMQ makes the message-broker concepts explicit:

Producer → Broker → Queue → Consumer

This makes it a useful technology for learning reliable asynchronous processing.

Why not Kafka?

Kafka is very strong for durable event streams, replayable logs, and many independent consumers processing event streams.

The immediate payment-processing problem is more naturally described as:

"Process this payment"

which is task/queue semantics rather than a stream-processing problem.

Kafka can absolutely be used in a payment architecture, but RabbitMQ is a more direct fit for this first worker-based design.

5. Local RabbitMQ Setup

RabbitMQ was run locally using Docker.

docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4-management

The important ports are:

5672   → AMQP/application connections
15672  → RabbitMQ Management UI

The Management UI was useful for observing queues and message states.

Python communicates with RabbitMQ using the Pika client library:

python -m pip install pika

The overall setup is:

Python Application
      ↓
     Pika
      ↓
RabbitMQ Server

6. RabbitMQ Server vs Pika

RabbitMQ is the actual server/broker.

Pika is the Python client library used to communicate with RabbitMQ.

Pika is not another server.

The Management UI is also not the broker. It is an administration/observability interface for RabbitMQ.

Conceptually:

Python
  ↓
Pika
  ↓
AMQP
  ↓
TCP
  ↓
RabbitMQ

7. Connection and Channel

A connection is the underlying communication connection to RabbitMQ.

The Pika code used:

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost")
)

ConnectionParameters

ConnectionParameters contains configuration describing how Pika should connect, such as the host and connection settings.

Example:

pika.ConnectionParameters("localhost")

means the broker is expected on the local machine using the default RabbitMQ/AMQP connection settings.

BlockingConnection

BlockingConnection provides Pika's synchronous/blocking interface.

Establishing and using the connection is performed synchronously from the Python program's point of view.

This was chosen for the initial experiments because it keeps RabbitMQ concepts separate from asyncio concepts.

Channel

A channel is a lightweight logical communication path over a RabbitMQ connection.

Conceptually:

One connection
   ├── Channel 1
   ├── Channel 2
   └── Channel 3

The channel is not another independent TCP connection.

When:

connection.close()

is called, the underlying connection is closed and its channels are no longer usable.

8. Queue Declaration

A queue can be declared using:

channel.queue_declare(
    queue="hello",
    durable=True,
)

queue_declare means:

Ensure that a queue with this name and configuration exists.

A producer and consumer can both declare the same queue. This means the consumer does not have to rely on the producer having started first.

The declarations must agree on important queue properties. Trying to redeclare an existing queue with conflicting properties can cause a channel error.

9. Durable Queue vs Durable Message

This distinction is important.

Durable queue
    ≠
Persistent message

durable=True means the queue definition should survive a broker restart.

It does not by itself guarantee that every message is persistent.

Reliable messaging therefore has multiple layers, including queue durability and message/publish durability.

10. Exchange

The simplified first mental model was:

Producer → Queue → Consumer

RabbitMQ's actual conceptual model is:

Producer
   ↓
Exchange
   ↓
Routing
   ↓
Queue
   ↓
Consumer

The producer publishes a message to an exchange.

The exchange determines which bound queues should receive the message.

This provides a major decoupling benefit:

The producer does not need to know which queues or consumers exist.

11. Default Exchange

The first experiment used:

channel.basic_publish(
    exchange="",
    routing_key="hello",
    body="Hello RabbitMQ",
)

An empty exchange name means the default exchange.

The default exchange has a special behavior: a queue is associated with its own queue-name routing key.

Therefore:

exchange = ""
routing_key = "hello"

effectively routes to the queue named:

hello

This is why the first experiment looked like the producer was publishing directly to a queue.

12. Binding a Queue to an Exchange

A queue is connected to an exchange using a binding.

For example:

channel.queue_bind(
    exchange="payment_events",
    queue="payment_processing_queue",
    routing_key="payment.created",
)

This means:

A message published to payment_events with routing key payment.created should be routed to payment_processing_queue.

Multiple queues can use the same routing key.

For example:

channel.queue_bind(
    exchange="payment_events",
    queue="payment_processing_queue",
    routing_key="payment.created",
)

channel.queue_bind(
    exchange="payment_events",
    queue="webhook_queue",
    routing_key="payment.created",
)

Then a single publication can be delivered to both queues, depending on the exchange type and bindings.

13. Exchange Types

Direct Exchange

A direct exchange uses exact routing-key matching.

Example:

payment_processing_queue ← payment.process
webhook_queue            ← payment.webhook

A message with:

routing_key = payment.process

is routed to the processing queue, not the webhook queue.

Direct exchanges are useful when exact routing is desired.

Fanout Exchange

A fanout exchange broadcasts a message to every queue bound to the exchange.

Example:

                  Fanout Exchange
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
     Processing      Webhook       Analytics

A single event can therefore be received independently by all subscribers.

Fanout is useful when many consumers should receive the same event.

Topic Exchange

A topic exchange supports pattern-based routing using dot-separated routing keys.

Example routing keys:

payment.created
payment.processing
payment.success
payment.failed
refund.created
refund.success

A queue bound with:

payment.*

matches one-word suffixes such as:

payment.created
payment.success
payment.failed

A queue bound with:

payment.#

can match multiple segments below the payment hierarchy.

Topic exchanges are useful when events follow a structured naming convention.

14. RabbitMQ Experiments Completed

Experiment 1 — Producer / Consumer

A producer published:

Hello RabbitMQ

to a queue named hello.

The consumer listened to that queue and printed:

Received: Hello RabbitMQ

This demonstrated:

Producer
  ↓
RabbitMQ
  ↓
Queue
  ↓
Consumer

Experiment 2 — Topic Exchange

A topic exchange was created with multiple queues and bindings.

Example topology:

payment_events
      │
      ├── payment_processing_queue
      │       payment.created
      │
      ├── webhook_queue
      │       payment.*
      │
      └── analytics_queue
              payment.#

Messages with different routing keys were sent and the expected queues received them.

This demonstrated that the producer only needs to know the exchange and routing key while the exchange handles queue routing.

15. Consumer Acknowledgements

RabbitMQ needs to know whether a delivered message has actually been handled by the consumer.

The message delivery and the acknowledgement are two separate concepts.

auto_ack=True

With:

channel.basic_consume(
    queue="hello",
    on_message_callback=callback,
    auto_ack=True,
)

RabbitMQ automatically treats the delivery as acknowledged when it is delivered to the consumer.

The consumer callback then runs independently from the broker's perspective.

Conceptually:

RabbitMQ
   ↓
Deliver message
   ↓
Automatic ACK
   ↓
Callback processes message

The problem is that if the worker crashes during processing, RabbitMQ has already considered the message completed.

The message may not be redelivered.

auto_ack=False

With:

channel.basic_consume(
    queue="hello",
    on_message_callback=callback,
    auto_ack=False,
)

RabbitMQ still delivers the message, but it does not automatically mark the delivery as completed.

The consumer must explicitly acknowledge it:

ch.basic_ack(
    delivery_tag=method.delivery_tag
)

This tells RabbitMQ:

I have successfully processed this particular delivery.

16. Meaning of Consumer Callback Parameters

A callback can receive:

def callback(ch, method, properties, body):
    ...

ch

The channel through which the message delivery occurred.

It can be used to send an acknowledgement back through that channel:

ch.basic_ack(...)

method

Contains delivery metadata.

One important field is:

method.delivery_tag

This identifies the delivery for acknowledgement purposes.

properties

Contains message metadata/properties.

body

Contains the actual message payload sent by the producer.

For example:

body.decode()

can turn the bytes payload into a normal Python string.

17. basic_consume() vs start_consuming()

These have different responsibilities.

channel.basic_consume(
    queue="hello",
    on_message_callback=callback,
    auto_ack=False,
)

registers the consumer and callback.

Then:

channel.start_consuming()

starts the consuming loop and waits for messages.

Conceptually:

basic_consume()
    ↓
Register callback

start_consuming()
    ↓
Wait for messages
    ↓
Message arrives
    ↓
Invoke callback
    ↓
Wait for next message

18. Why ACK Is Important

The purpose of acknowledgement is not to prove that the payment succeeded.

It proves that the worker successfully handled the queue message.

For example:

Receive message
   ↓
Process work
   ↓
Work handled safely
   ↓
ACK

If the worker fails before ACK:

Receive message
   ↓
Process
   ↓
Worker crashes
   ↓
NO ACK

RabbitMQ can then make the message eligible for redelivery.

This is the foundation of at-least-once delivery.

19. At-Least-Once Delivery

At-least-once delivery means the system attempts to ensure that the message is delivered at least once, but it does not guarantee exactly-once processing.

A message can therefore be processed more than once if an acknowledgement is not successfully completed.

Example:

Message
  ↓
Worker A receives it
  ↓
Worker processes it
  ↓
Worker crashes before ACK
  ↓
RabbitMQ redelivers
  ↓
Worker B receives it

Therefore:

Consumers must be designed to tolerate duplicate delivery.

This is especially important for payments.

20. Why Duplicate Delivery Is Not the Main Problem

It is tempting to think:

"We should make sure RabbitMQ never delivers a message twice."

That is not the right mental model for reliable distributed processing.

The more useful model is:

Duplicate delivery can happen; the consumer must handle it safely.

This is similar to the API idempotency work already implemented in the payment gateway.

The queue protects message delivery, while the worker protects business correctness.

21. Payment Worker and Idempotent Processing

A future payment-processing message can look conceptually like:

{
  "event": "PAYMENT_PROCESS",
  "payment_id": "pay_123"
}

The worker receives the payment ID and calls:

process_payment(payment_id)

A first safety check is the gateway's current payment state.

If the payment is already terminal:

SUCCESS

or:

FAILED

then duplicate delivery should not cause another PSP payment creation.

The worker should safely treat the duplicate message as already handled and ACK it.

However, local DB status alone is not sufficient when an external PSP interaction is uncertain.

22. Critical Failure Case: PSP Success + Gateway DB Failure

Consider:

Worker
  ↓
PSP
  ↓
SUCCESS
  ↓
Gateway attempts DB update
  ↓
Database fails
  ↓
ACK never happens

Now RabbitMQ can redeliver the processing message.

The gateway database may still say:

PROCESSING

while the PSP says:

SUCCESS

The worker must not simply see PROCESSING and create the payment with the PSP again.

That could produce a duplicate charge.

The worker must instead determine whether the provider-side payment attempt already exists and retrieve its state.

23. Provider-Side Payment Reference

This is therefore a required part of the eventual payment design.

The gateway payment should be correlated with the external provider payment attempt.

Conceptually:

Gateway
payment_id = pay_101

        ↕

PSP
provider_payment_id = psp_847291

The provider-side reference becomes important for both:

RabbitMQ redelivery

PSP callbacks

When the worker receives a redelivered job, it can determine whether an external payment attempt already exists.

For example:

pay_101
   ↓
provider_payment_id = psp_847291
   ↓
GET provider status
   ↓
SUCCESS / FAILED / PROCESSING / NOT_FOUND

This allows the gateway to recover the actual external state rather than creating a new provider payment.

24. Handling ACK Failure and PSP Uncertainty

If the worker cannot safely complete its work, it should not acknowledge the message merely to make the queue look clean.

For example:

PSP result = SUCCESS
        ↓
DB update fails
        ↓
retry DB update

Database updates can be retried with controlled backoff when the failure is temporary.

Conceptually:

1s → 2s → 4s → 8s → ...

with a bounded retry window.

The worker should not immediately consider the payment failed merely because its database update failed.

If the worker cannot safely finish the operation within the allowed retry window, it should leave the message unacknowledged or otherwise make the job eligible for another processing attempt according to the queue strategy.

The important principle is:

Do not ACK work that has not been safely handled.

The worker does not need to kill the entire worker process as the normal solution. The important unit is the message-processing attempt. The worker process can continue handling other work while the failed message is retried according to the messaging strategy.

25. Eventual Consistency

This queue behavior connects directly to the payment gateway's eventual-consistency design.

A temporary state mismatch can occur:

Gateway DB = PROCESSING
PSP         = SUCCESS

The gateway should not attempt to rollback a PSP payment that may already have succeeded.

Instead it should converge toward a consistent state through:

provider callbacks,

provider status retrieval,

retries,

exponential backoff,

eventual manual reconciliation.

The objective is:

Gateway DB = SUCCESS
PSP         = SUCCESS

26. Why Worker Logic and PSP Logic Must Be Separated

The worker should invoke a payment-processing operation.

The payment service should contain the business rules around:

loading the payment,

deciding whether the payment is processable,

selecting the provider,

calling the provider,

interpreting provider outcomes,

applying valid payment-state transitions,

atomically updating payment and payment history.

RabbitMQ is only the mechanism that invokes this operation asynchronously.

The business logic should not become dependent on RabbitMQ itself.

Conceptually:

RabbitMQ Worker
      ↓
payment_id
      ↓
PaymentService.process_payment()
      ↓
PaymentServiceProvider
      ↓
PSP

This means the same process_payment() operation can first be tested synchronously and later invoked by a worker without changing the core business logic.

27. Eventual Payment Architecture

The payment gateway is moving toward:

                        Merchant
                           │
                           │ POST /payments
                           ▼
                    Payment Creation API
                           │
                           ▼
                     PaymentService
                           │
                    DB Transaction
               ┌───────────┼───────────┐
               │           │           │
           Payment      History    Idempotency
               └───────────┼───────────┘
                           │
                         COMMIT
                           │
                           ▼
                     201 PROCESSING

                           │
                           ▼
                 Payment Processing Message
                           │
                           ▼
                        RabbitMQ
                           │
                           ▼
                   Payment Worker
                           │
                           ▼
              process_payment(payment_id)
                           │
                           ▼
                PaymentServiceProvider
                           │
                           ▼
                          PSP
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           SUCCESS       FAILED      UNCERTAIN
              │            │            │
              ▼            ▼            ▼
        Atomic state    Atomic state   Stay PROCESSING
          update          update       + recovery
              │            │            │
              └──────┬─────┴────────────┘
                     ▼
                 Webhook Event
                     │
                     ▼
                Webhook Queue
                     │
                     ▼
                Webhook Worker
                     │
                     ▼
                   Merchant

28. Why Webhooks Are a Separate Queue Problem

Payment processing and webhook delivery are different asynchronous responsibilities.

Payment processing queue

Payment created
    ↓
Payment processing queue
    ↓
Payment worker
    ↓
PSP

Purpose:

Process the payment without making the merchant HTTP request wait for external processing.

Webhook delivery queue

Payment status changed
    ↓
Webhook event
    ↓
Webhook queue
    ↓
Webhook worker
    ↓
Merchant endpoint

Purpose:

Deliver payment lifecycle updates without making payment processing wait for the merchant webhook server.

These are separate reliability boundaries.

29. Merchant Status Synchronization

The payment creation response is an initial acknowledgement:

{
  "payment_id": "pay_101",
  "status": "PROCESSING"
}

It does not represent the final payment outcome.

The merchant should synchronize its internal payment attempt using webhook events for lifecycle changes such as:

SUCCESS
FAILED

The gateway can still provide a payment-status API for querying the latest gateway state and reconciliation.

30. Transactional Outbox: The Next Reliability Problem

Introducing RabbitMQ creates another distributed-system failure window.

A naive implementation might do:

DB COMMIT
   ↓
Publish RabbitMQ message

But what if:

DB COMMIT ✅
RabbitMQ publish ❌

Now:

Payment = PROCESSING
Queue   = no processing message

The payment may remain stuck without a processing job.

The reverse problem can also happen:

Publish RabbitMQ message ✅
DB COMMIT ❌

Now the queue contains work for a payment that did not successfully commit.

This is the classic gap between two independent systems: the database and the message broker.

31. Transactional Outbox Pattern

The transactional outbox pattern solves this by placing an event record in the same database transaction as the business change.

Instead of:

Payment commit
   ↓
RabbitMQ publish

use:

BEGIN
    Payment
    PaymentHistory
    Idempotency
    OutboxEvent
COMMIT

Conceptually:

outbox_events
----------------------------
event_id
event_type
aggregate_id
payload
status
created_at

For example:

{
  "event_type": "PAYMENT_PROCESS",
  "payment_id": "pay_123"
}

After the transaction commits, a publisher can read the outbox and publish the event to RabbitMQ.

The important guarantee becomes:

Payment exists ✅
Outbox event exists ✅

as one atomic database result.

If the publisher crashes before RabbitMQ receives the message, the outbox record remains available and can be retried.

Transactional outbox is therefore the next reliability layer to study before making the DB-to-RabbitMQ handoff production-grade.

32. Current Learning Progress

The following RabbitMQ concepts have been studied and experimentally verified:

RabbitMQ server/broker

Pika client

Connection

Channel

Queue declaration

Durable queues

Producer

Consumer

Exchange

Queue bindings

Default exchange

Direct exchange

Fanout exchange

Topic exchange

Routing keys

Consumer callbacks

basic_consume()

start_consuming()

Automatic acknowledgement

Manual acknowledgement

delivery_tag

Unacknowledged messages

Redelivery

At-least-once delivery

Idempotent consumer reasoning

Payment-processing queue architecture

PSP uncertainty and provider-side payment references

Transactional outbox as the next reliability topic

33. Next Implementation Direction

The next implementation stage should not jump directly into the full payment gateway messaging architecture.

The recommended sequence is:

Study RabbitMQ fundamentals
        ↓
Understand ACK/redelivery
        ↓
Understand exchange/routing
        ↓
Build Payment Worker
        ↓
Invoke process_payment(payment_id)
        ↓
Test SUCCESS / FAILED / TIMEOUT
        ↓
Model provider_payment_id
        ↓
Handle PSP status lookup on uncertainty/redelivery
        ↓
Add PSP callback handling
        ↓
Add webhook delivery worker
        ↓
Study and implement transactional outbox

The core design principle is:

The queue provides reliable asynchronous work delivery; the payment domain provides idempotent and state-safe processing; the PSP remains an independent system whose state must eventually converge with the gateway.