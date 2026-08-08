# Payment Gateway Backend
# Database - 03 Transaction Boundaries

---

# 1. Purpose of this Document

This document explains **how we use transactions in our Payment Gateway**.

It does **not** explain:

- ACID properties
- What transactions are
- Isolation levels
- Database theory

Instead, it answers the questions we discussed while designing our Signup API.

- Where should a transaction begin?
- Where should it end?
- Who should own the transaction?
- Why shouldn't repositories call `commit()`?
- Which operations belong inside the transaction?
- Which operations should happen after the transaction?
- How will this design scale to Payments and Refunds?

---

# 2. What is a Transaction Boundary?

A business operation usually consists of multiple database operations.

For example, Signup is not just:

```
Create Merchant
```

It is

```
Create Merchant

↓

Create Refresh Token

↓

Return Success
```

All these operations together represent **one business operation**.

The transaction boundary should cover the **entire business operation**, not individual repository methods.

---

# 3. Signup Transaction

Our Signup API performs the following steps.

```
Receive Request

↓

Validate Input

↓

Check Email Exists

↓

Hash Password

↓

Create Merchant

↓

Create Refresh Token

↓

Commit

↓

Return Response
```

Notice that **only part of this flow needs the database transaction.**

---

# 4. What Should Be Inside the Transaction?

For our Signup API, the transaction includes only the operations that modify database state.

```
BEGIN TRANSACTION

↓

MerchantRepository.create()

↓

RefreshTokenRepository.create()

↓

COMMIT
```

Everything outside this block is either validation or HTTP handling.

---

# 5. What Should NOT Be Inside the Transaction?

This was one of the architectural decisions we made.

These operations do not need to be inside the transaction.

```
Validate Request

Check Email Format

Hash Password

Create Response Object

Set Cookie

Serialize JSON
```

Why?

Because none of these modify database state.

Keeping them outside the transaction means the transaction stays as short as possible.

Short transactions reduce database locks and improve scalability.

---

# 6. Why Doesn't Repository Call commit()?

This was one of the most important discussions we had.

Imagine the Repository does this.

```
MerchantRepository.create()

↓

commit()
```

Then Signup continues.

```
RefreshTokenRepository.create()

↓

Exception
```

Now our database looks like this.

```
Merchant

✓ Created

Refresh Token

✗ Missing
```

The merchant exists,

but no refresh session exists.

The business operation is only half complete.

That should never happen.

---

Instead, the Repository only performs persistence.

```
MerchantRepository.create()

↓

Return
```

The Service decides when the business operation has successfully completed.

Only then does it commit.

---

# 7. Why Service Owns the Transaction

The Service understands the complete business flow.

```
AuthService.signup()

↓

MerchantRepository

↓

RefreshTokenRepository

↓

Commit
```

The Repository does not know that another repository will be called later.

Only the Service has the complete picture.

Therefore,

the Service owns the transaction boundary.

---

# 8. Why One Commit?

Suppose Signup performs

```
Create Merchant

↓

Commit

↓

Create Refresh Token

↓

Commit
```

Now there are two transactions.

If the second one fails,

the first one is already permanent.

This leaves the database in an inconsistent business state.

Instead,

Signup should perform

```
Create Merchant

↓

Create Refresh Token

↓

Commit
```

One business operation.

One transaction.

One commit.

---

# 9. Why Check Email Before Creating Merchant?

Our Signup flow starts with

```
Find Merchant by Email
```

before inserting anything.

This is not part of the write transaction.

It is a business validation.

If the email already exists,

there is no reason to start creating new records.

The transaction only begins when we are actually ready to modify the database.

---

# 10. Why Hash Password Before Persistence?

Hashing happens before storing the Merchant.

```
Password

↓

bcrypt

↓

Hashed Password

↓

MerchantRepository.create()
```

Hashing is a CPU operation.

It does not require the database.

Therefore,

it should happen before database writes.

---

# 11. Why Store Refresh Token Before Commit?

Our Signup operation creates both

```
Merchant

Refresh Token
```

These represent one authenticated session.

If we commit the Merchant but fail to store the Refresh Token,

the merchant account exists,

but the login session cannot be restored.

That is an incomplete Signup.

Therefore,

both records are committed together.

---

# 12. Why Router Sets Cookie After Service Returns

The Router performs

```
AuthService.signup()

↓

response.set_cookie()

↓

Return SignupResponse
```

Notice

The Router waits for the Service to finish.

Why?

Because the Service has already completed the transaction successfully.

If Signup fails,

Router never sets the cookie.

This prevents sending a Refresh Token for a failed Signup.

---

# 13. What Happens If Refresh Token Insert Fails?

Suppose

```
MerchantRepository.create()

↓

RefreshTokenRepository.create()

↓

Database Error
```

The Service catches the exception.

```
Rollback
```

After rollback

```
Merchant

✗ Removed

Refresh Token

✗ Removed
```

The database returns to its previous consistent state.

The client receives an error.

From the user's perspective,

Signup never happened.

---

# 14. Why Return Success Only After Commit?

Imagine this sequence.

```
Return Success

↓

Commit
```

Suppose Commit fails.

The client already believes Signup succeeded.

But the Merchant doesn't exist.

This is a serious bug.

Instead,

our flow is

```
Commit

↓

Return Success
```

The client only receives success after the transaction has completed.

---

# 15. Future Payment Flow

Signup today

```
Merchant

↓

Refresh Token

↓

Commit
```

Future Payment API

```
Create Payment

↓

Reserve Balance

↓

Create Ledger Entry

↓

Create Audit Record

↓

Commit
```

Notice

The business operation becomes larger,

but the design stays exactly the same.

One business operation.

One transaction boundary.

---

# 16. Common Mistakes

## ❌ Repository calls commit()

Repository should only persist data.

Transaction ownership belongs to the Service.

---

## ❌ Multiple commits during one business operation

Signup is one business operation.

It should have one commit.

---

## ❌ Returning success before commit

The client should never receive success before the transaction completes.

---

## ❌ Setting cookies before transaction succeeds

HTTP response construction should happen only after the Service finishes successfully.

---

## ❌ Mixing HTTP work with transaction logic

The Router owns HTTP.

The Service owns business logic.

The Repository owns persistence.

Each layer should remain focused on its responsibility.

---

# 17. Key Takeaways

✔ A transaction boundary should represent a complete business operation.

✔ The Service owns transaction boundaries.

✔ Repositories never decide when to commit.

✔ Signup performs one commit, not multiple.

✔ Password hashing is outside the transaction.

✔ Cookie creation is outside the transaction.

✔ Success is returned only after commit succeeds.

✔ Rollback ensures the database never contains half-completed business operations.

---

# Interview Notes

★★★★★ Why shouldn't Repository call commit()?

Because a business operation may involve multiple repositories. The Service is the only layer that knows when the entire operation has completed successfully.

---

★★★★★ Why use one commit for Signup?

Signup is a single business operation. Committing once ensures all database changes succeed or fail together.

---

★★★★☆ What belongs inside a transaction?

Only the database modifications required for the business operation.

---

★★★★☆ Why is password hashing outside the transaction?

Because it is a CPU operation and does not modify database state.

---

★★★★☆ Why are cookies set after the Service returns?

Because HTTP responses should only be constructed after the business transaction has completed successfully.

---

# Connection With Our Project

```
POST /auth/signup

↓

Router

↓

AuthService.signup()

│

├── Check email

├── Hash password

│

├──── BEGIN TRANSACTION ────┐

│                           │

├── MerchantRepository.create()

├── RefreshTokenRepository.create()

│

└──────── COMMIT ───────────┘

↓

Return merchant + tokens

↓

Router

↓

Set HttpOnly Refresh Cookie

↓

Return SignupResponse

↓

Client
```

**The important idea is this:**

Our transaction is **not tied to a repository method**.

It is tied to the **business operation** called **Signup**.

That is the reason our transaction boundary lives in the **Service Layer**.