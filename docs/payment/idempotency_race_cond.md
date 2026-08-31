# Idempotency Race Condition Handling

## Problem

Two requests can arrive at nearly the same time with the same merchant and idempotency key.

Both requests may first check:

```text
Idempotency Key does not exist
```

and then both attempt to create the record.

A normal existence check is therefore not enough.

---

## Database Guarantee

The `idempotency_keys` table has:

```python
UniqueConstraint(
    "merchant_id",
    "idempotency_key",
    name="uq_merchant_idempotency_key",
)
```

This makes the database the final concurrency authority.

If two transactions try to insert the same `(merchant_id, idempotency_key)` pair, only one succeeds.

The other receives an `IntegrityError`.

---

## Application Handling

The service handles only the specific idempotency constraint violation.

```python
try:
    IdempotencyKeyRepository.create(
        db=db,
        idempotency_record=idempotency_record,
    )

except IntegrityError as exc:

    if exc.orig.diag.constraint_name != "uq_merchant_idempotency_key":
        raise

    db.rollback()

    existing_record = IdempotencyKeyRepository.get_by_key(
        db=db,
        merchant_id=merchant_id,
        idempotency_key=request.idempotency_key,
    )

    if existing_record is None:
        raise RuntimeError(
            "Idempotency record not found after unique constraint violation."
        )

    if existing_record.request_hash != request_hash:
        raise HTTPException(
            status_code=409,
            detail="Idempotency key has already been used for a different request.",
        )

    return PaymentCreateResponse(
        **existing_record.response_snapshot
    )
```

### Why the rollback?

The losing request has an aborted transaction.

`rollback()` clears that failed transaction and allows the same SQLAlchemy session to be used again.

The losing request's uncommitted `Payment` and `PaymentHistory` records are also discarded.

It can then query the idempotency table in a new transaction and retrieve the record created by the winning request.

---

## Race Condition Flow

```text
Request A                         Request B

get_by_key → NONE                get_by_key → NONE
     ↓                                ↓
Create Payment                   Create Payment
     ↓                                ↓
Create History                  Create History
     ↓                                ↓
Insert Idempotency              Insert Idempotency
     ↓                                ↓
   SUCCESS                 UNIQUE constraint violation
     ↓                                ↓
  COMMIT                         ROLLBACK
     ↓                                ↓
                                Re-query key
                                      ↓
                              Find A's record
                                      ↓
                              Compare request hash
                                      ↓
                              Replay A's response
```

Result:

```text
Exactly one Payment
Exactly one PaymentHistory
Exactly one IdempotencyKey
Both requests receive the same payment_id
```

---

## Testing the Race Condition

The race was forced manually by temporarily adding a delay after confirming that the idempotency record did not already exist:

```python
# Temporary race-condition test only
time.sleep(5)
```

This allowed two concurrent requests to both reach the insertion point before either completed.

The test was performed through Swagger using the same:

```text
merchant_id
idempotency_key
request payload
```

The observed output included:

```text
201 Created

IntegrityError:
duplicate key value violates unique constraint
"uq_merchant_idempotency_key"

201 Created
```

Both responses contained the **same `payment_id`**.

This confirmed that:

* the database unique constraint detected the race,
* only one idempotency record won,
* the losing request did not create a second payment,
* the winning payment's response was replayed to the concurrent request.

The temporary delay and debug print were used only for testing and should be removed afterward.

## Core Principle

The race condition is not prevented by the initial `get_by_key()` check.

The database unique constraint provides the concurrency guarantee, while the application handles the losing request and converts the constraint violation into normal idempotency behavior.

> **Database constraint = concurrency protection.**
> **Application logic = correct response to the race.**
