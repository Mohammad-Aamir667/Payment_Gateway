# Importance of Rollback in Idempotency

During concurrent payment requests using the same idempotency key, one request may successfully insert the idempotency record while another request receives a unique-constraint violation.

```text
Request B
   ↓
INSERT idempotency key
   ↓
UNIQUE constraint violation
   ↓
Transaction fails
```

At this point, the SQLAlchemy `Session` is still alive, but its current transaction is failed. The same session cannot perform another database operation until the failed transaction is rolled back.

```python
db.rollback()
```

Rollback resets the session and allows it to start a new transaction.

The losing request can then reuse the same session:

```text
IntegrityError
      ↓
db.rollback()
      ↓
Query existing idempotency record
      ↓
Compare request hash
      ↓
Same → replay response
Different → 409 Conflict
```

The rollback also removes all uncommitted changes made by the losing request, such as its temporary `Payment` and `PaymentHistory` records.

Therefore:

> **Rollback is required in the idempotency race because we intentionally continue using the same database session after the failed transaction.**
