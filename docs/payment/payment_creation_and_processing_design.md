# Payment Creation and Processing: Design Notes

## Purpose

This document records the reasoning behind the payment API and
`PaymentService` design. It focuses on payment creation, safe reuse of
`process_payment()` by a background worker, provider-status handling,
and error propagation.

The RabbitMQ topology, consumer behavior, retry queues, dead-letter
queue (DLQ), and transactional outbox are intentionally outside this
document. The outbox pattern is a planned improvement for more reliable
publication after a database commit.

------------------------------------------------------------------------

## 1. The API endpoint has two responsibilities

The endpoint:

``` python
@router.post(
    "",
    response_model=CreatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    request: CreatePaymentRequest,
    merchant: Merchant = Depends(get_authenticated_merchant),
    db: Session = Depends(get_db),
) -> CreatePaymentResponse:
    payment_service = PaymentService()
    result = payment_service.create_payment(
        db=db,
        merchant_id=merchant.merchant_id,
        request=request,
    )

    if result.should_process:
        publish_payment_processing(
            payment_id=result.response.payment_id,
        )

    return result.response
```

keeps the HTTP layer thin. `PaymentService` creates or replays the
payment result; the route publishes a processing job only when the
service says this is a newly created payment.

The API acknowledges payment creation. It does **not** wait for the PSP
to finish processing the payment.

## 2. How `create_payment()` validates and creates a payment

`PaymentService.create_payment()` follows an intentional order. It
validates the request and the merchant's configuration before creating
the gateway payment and its supporting records.

1.  **Hash the request.** Build a canonical representation of the
    meaningful fields---merchant payment method, amount, currency, and
    payment metadata---and generate a request hash. The hash lets the
    service determine whether a repeated idempotency key represents the
    same request.
2.  **Check the idempotency record.**
    -   If the key exists and the hash matches, return the previously
        stored response with `should_process=False`. This is a replay of
        the original result, not a new payment.
    -   If the key exists but the hash differs, return HTTP
        `409 Conflict`. A merchant must not reuse the same key for a
        different payment request.
    -   If no record exists, continue validation.
3.  **Validate the merchant payment method.** Fetch it for the
    authenticated merchant, so the request cannot use another merchant's
    payment-method configuration. Reject it if it does not exist or is
    disabled.
4.  **Validate the gateway payment method.** Fetch the underlying
    gateway payment method and reject the request if it is missing or
    inactive.
5.  **Create the gateway payment.** Create the `Payment` with status
    `PROCESSING`. At this point, the gateway is acknowledging that it
    has accepted the payment for asynchronous processing---not that the
    PSP has completed it.
6.  **Create the initial payment history.** Record the initial
    transition from no prior state (`NULL`) to `PROCESSING`.
7.  **Prepare and persist the idempotency result.** Build the API
    response snapshot and store it with the merchant ID, idempotency
    key, request hash, and payment reference. The response snapshot
    allows an identical retry to receive the original response.
8.  **Commit the database transaction.** The payment, initial history,
    and idempotency record are committed together. Only after a new
    payment has been committed does the service return
    `should_process=True`.

The API route uses the internal `CreatePaymentResult` to decide whether
to publish a processing message:

``` python
@dataclass
class CreatePaymentResult:
    response: CreatePaymentResponse
    should_process: bool
```

``` python
result = payment_service.create_payment(...)

if result.should_process:
    publish_payment_processing(
        payment_id=result.response.payment_id,
    )

return result.response
```

**Why this matters:** an identical request retry returns the saved
response with `should_process=False`, so the route does not publish
another job for that retry. A new payment returns `should_process=True`,
so the route publishes its payment ID for asynchronous processing.

This prevents unnecessary duplicate publications caused by ordinary API
retries, but it does not guarantee that database commit and RabbitMQ
publication are atomic. If the database commit succeeds and publishing
fails, a payment may exist without a queued job. A **transactional
outbox** is planned for that durability gap. The concurrent
idempotency-key race and its database-constraint handling are documented
separately.

------------------------------------------------------------------------

## 3. Why `process_payment()` is reusable by a worker

`process_payment(db, payment_id)` contains payment-processing business
logic and returns a `Payment`. It does not depend on an HTTP request or
a RabbitMQ channel.

That allows different callers---currently the background worker---to
invoke the same business operation without duplicating
provider-selection, reconciliation, or payment-state logic.

At a high level, it:

1.  Loads the gateway payment.
2.  Checks whether it is still `PROCESSING`.
3.  Loads and validates the merchant's configured payment method and the
    gateway payment method.
4.  Selects the provider adapter.
5.  Determines whether to retrieve an existing provider payment or
    initiate one.
6.  Interprets the provider result.
7.  Persists the provider reference and/or terminal state as
    appropriate.

### Missing or already-terminal payments

If the gateway payment does not exist, `PaymentNotFoundError` is raised.
If the payment is no longer `PROCESSING`, the method returns it without
initiating another provider payment. That makes a duplicate job for an
already-terminal payment a normal, safely completed outcome rather than
a reason to create another provider transaction.

Missing merchant-payment-method or payment-method records raise specific
application exceptions. These indicate invalid or inconsistent gateway
data, not a transient provider communication problem. The worker can
classify them as non-retryable according to the current job policy.

------------------------------------------------------------------------

## 4. Resolve an existing PSP payment before initiating another

A central rule is:

> **Recover an existing provider payment when possible; do not blindly
> create another one.**

The provider decision is sequential:

1.  **Gateway already has `provider_payment_id`:** call
    `get_payment_status()` for that provider payment.
2.  **Gateway does not have a provider ID:** call
    `find_payment_by_gateway_id()` using the gateway's payment ID.
3.  **A provider payment is found:** use the returned provider result
    directly. The lookup already returns the provider payment's current
    status, so there is no need to make a second status request at this
    point.
4.  **No provider payment is found:** call `initiate_payment()`.

This sequence is important after an ambiguous outcome, such as a timeout
or a lost response. The PSP might have created the transaction even
though the gateway did not receive or persist its provider ID. Looking
up by the gateway payment ID gives the gateway a chance to recover that
existing transaction instead of initiating another one.

The provider's `gateway_payment_id` reference is therefore useful for
reconciliation when the gateway never received `provider_payment_id`.

------------------------------------------------------------------------

## 5. Provider communication errors are not payment failures

The provider adapter has a common `ProviderCommunicationError` base
class, with more specific errors such as `ProviderTimeoutError`,
`ProviderResponseLostError`, `ProviderConnectionError`, and
`ProviderInternalError`.

`process_payment()` catches the base class around provider calls:

``` python
try:
    # get status, look up an existing provider payment,
    # or initiate a provider payment
    ...
except ProviderCommunicationError:
    db.rollback()
    raise
```

Because the specific provider exceptions inherit from
`ProviderCommunicationError`, this handler catches them too.

The rollback cleans up the current database transaction. The bare
`raise` then re-raises the **same exception**, allowing the worker to
classify it. `process_payment()` does not convert a timeout into
`PaymentStatus.FAILED`: a communication failure does not establish that
the provider transaction failed. The PSP may have processed the payment
even if the gateway did not receive the response.

The layers have separate responsibilities:

-   **Provider adapter:** translates known transport/provider failures
    into meaningful provider exceptions.
-   **`PaymentService.process_payment()`:** performs required database
    cleanup and propagates provider communication failures.
-   **Worker:** maps exceptions to a job outcome such as `RETRY` or
    `DISCARD`.
-   **Consumer:** translates that job outcome into RabbitMQ ACK/NACK
    behavior.

This prevents payment business logic from depending directly on
RabbitMQ.

------------------------------------------------------------------------

## 6. Persist the provider reference even while status is `PROCESSING`

Whenever the provider returns a `provider_payment_id` and the gateway
does not yet have one, `process_payment()` stores it on the gateway
payment.

If the provider result is `PROCESSING` and a provider ID is available,
the method commits that reference and returns the payment without
creating a new payment-history transition.

Why?

-   The gateway already created the initial `PROCESSING` payment and its
    initial history record during payment creation.
-   `PROCESSING → PROCESSING` is not a meaningful status transition, so
    it does not need another history entry.
-   The provider reference must be persisted so a later job or
    reconciliation attempt can query the existing PSP transaction.
-   A provider result of `PROCESSING` is not a failure. The gateway
    should not mark the payment `FAILED` simply because the PSP has not
    reached a terminal state yet.

The current method therefore returns safely after saving the provider
reference. A later processing attempt can call `get_payment_status()`
using that ID.

For terminal provider results, the gateway maps `SUCCESS` or `FAILED` to
the corresponding gateway status, updates the payment, creates a
`PaymentHistory` entry for `PROCESSING → SUCCESS` or
`PROCESSING → FAILED`, and commits the changes together. If the database
update fails, it rolls back and re-raises the exception.

------------------------------------------------------------------------

## 7. Why the gateway needs an `UNKNOWN` provider status

The gateway should not assume that every response from an external PSP
will always contain a status it already understands. A provider could
introduce a new status, return a malformed response, or change its
response contract.

The provider adapter should normalize the received status into the
gateway's internal `ProviderPaymentStatus`. If the raw value does not
match a recognized status, it can represent the result as `UNKNOWN` and
preserve the raw status for diagnostics, for example:

``` python
try:
    status = ProviderPaymentStatus(raw_status)
except (ValueError, TypeError):
    status = ProviderPaymentStatus.UNKNOWN
```

The exact normalization belongs in the adapter that parses the PSP
response. `UNKNOWN` is a defensive status in the **gateway's internal
representation**; it does not mean the simulated PSP must treat
`UNKNOWN` as one of its normal business statuses.

### Why not map an unknown status to `FAILED` or `PROCESSING`?

-   Mapping it to `FAILED` would assert that the payment failed when the
    gateway does not actually know that.
-   Mapping it directly to `PROCESSING` would hide the fact that the
    provider returned a status the gateway could not interpret.

Keeping `UNKNOWN` preserves that distinction. It says: **the gateway
cannot safely interpret the provider's status**. The gateway must not
treat this as a confirmed payment failure or blindly proceed as though
the provider response were trustworthy and understood.

In the current service design, an unrecognized status is represented by
`UnknownProviderStatusError` rather than being mapped to a terminal
gateway status. The worker classifies this error according to the
current policy; it is intended to be non-retryable under the present
classification unless that policy is deliberately changed. Later,
bounded retries, reconciliation, and DLQ handling can provide a more
complete operational response to persistent unknown statuses.

The reason for this defensive layer is not that PSPs are inherently
unreliable. It is that an external system's contract can change or a
response can be malformed, and the gateway must preserve payment
correctness when it cannot confidently interpret the result.

------------------------------------------------------------------------

## 8. Unexpected exceptions and propagation

Not every exception is a known provider communication error. A
programming bug, unexpected response shape, or other unanticipated
runtime failure may raise something such as `KeyError`, `TypeError`, or
`AttributeError`.

The code should not convert every unexpected exception into
`ProviderCommunicationError`, because that would incorrectly claim it
was a known communication failure.

If `process_payment()` does not catch an unexpected exception, Python
propagates it to its caller. The worker is the boundary that can log the
unexpected exception and map it to the current job policy. In the
current learning-stage policy, unexpected job-level exceptions are
logged and discarded so a single bad job does not terminate the worker.
The consumer then ACKs a `DISCARD` result.

This is a deliberate temporary trade-off: ACKing a discarded job removes
it from the queue, so the job is lost rather than retained for
investigation. Later, a DLQ and bounded retry policy can replace that
behavior. Full process crashes, interpreter termination, and sudden
server/OS loss are separate infrastructure-level failure scenarios and
are intentionally deferred.

------------------------------------------------------------------------

## 9. Key design decisions to remember

-   Payment creation and PSP processing are separate: the API creates
    the gateway payment and acknowledges it; the worker processes it
    asynchronously.
-   Idempotency replays the original response and prevents the route
    from publishing another job for an ordinary duplicate request.
-   The database uniqueness constraint protects concurrent
    idempotency-key requests.
-   `process_payment()` is reusable because it contains payment business
    logic rather than HTTP or RabbitMQ behavior.
-   Existing provider payments are looked up before a new provider
    payment is initiated.
-   A timeout or lost response is uncertainty, not proof of payment
    failure.
-   Provider communication exceptions are rolled back and re-raised so
    the worker can classify them.
-   A provider `PROCESSING` result saves the provider reference and
    returns without inventing a new history transition.
-   `UNKNOWN` prevents an unrecognized provider status from being
    silently misclassified as success, failure, or ordinary processing.
-   Unexpected exceptions are contained at the worker boundary under the
    current temporary policy; retry limits, DLQ, and
    infrastructure-level recovery are future work.
-   A transactional outbox is planned to close the
    database-commit/message-publication gap.
