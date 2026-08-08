# N + 1 Query Problem

## Purpose

Understand the N + 1 Query Problem, why it occurs, and when it should be optimized.

---

# What Is the N + 1 Query Problem?

The N + 1 Query Problem occurs when an application executes:

- 1 query to retrieve a collection of records.
- N additional queries to retrieve related data for each record.

As the number of records grows, the number of database queries grows linearly.

---

# Example

Retrieve all payment methods configured by a merchant.

```python
merchant_payment_methods = repository.get_by_merchant(...)

for merchant_payment_method in merchant_payment_methods:

    payment_method = payment_method_repository.get_by_id(
        ...
    )
```

If the merchant has four payment methods:

```
1 Query

↓

MerchantPaymentMethod

+

4 Queries

↓

PaymentMethod

=

5 Total Queries
```

This is called the **N + 1 Query Problem**.

---

# Why Is It a Problem?

The issue is **not** that the database query itself is slow.

The issue is repeatedly communicating between the application and the database.

Example:

```
Application

↓

Database

↓

Application

↓

Database

↓

Application

↓

Database
```

Each query introduces an additional database round trip.

---

# Common Solution

Instead of retrieving related records one at a time, retrieve them together using a SQL JOIN.

Example:

```sql
SELECT
    mpm.*,
    pm.code,
    pm.display_name
FROM merchant_payment_methods mpm
JOIN payment_method pm
ON mpm.payment_method_id = pm.payment_method_id
WHERE mpm.merchant_id = ?;
```

Now only **one query** retrieves all required information.

---

# When Should It Be Optimized?

Optimize when:

- A large number of related records are loaded.
- The additional database round trips noticeably affect performance.

Examples:

- Orders → Order Items
- Users → Posts
- Companies → Employees

For very small datasets (for example, a merchant having only a few payment methods), a simple implementation may be acceptable because the performance impact is negligible.

---

# How to Recognize It

A common indicator is a database query executed inside a loop.

Example:

```python
parents = repository.get_all()

for parent in parents:
    child = repository.get_by_id(...)
```

Whenever a query is executed repeatedly inside a loop, consider whether the data can be retrieved using a JOIN or another optimized approach.

---

# Summary

```
1 Query

↓

Retrieve Parent Records

↓

Loop

↓

N Queries

↓

Retrieve Related Records

↓

N + 1 Queries
```

The N + 1 Query Problem is a performance issue caused by executing one database query for each related record instead of retrieving all required data in a single query.