# Payment Gateway Backend
# API - Signup Implementation

---

# 1. Purpose of this Document

This document does **not** explain the Signup API contract.

The request schema, response schema, validations, and endpoint design are documented separately.

Instead,

this document explains **why the Signup implementation looks the way it does**.

It captures the architectural decisions made while implementing the API.

---

# 2. High-Level Flow

```
HTTP Request

↓

Router

↓

AuthService.signup()

↓

Hash Password

↓

Create Merchant

↓

Generate Tokens

↓

Hash Refresh Token

↓

Store Refresh Token

↓

Commit

↓

Router

↓

model_validate()

↓

Set Refresh Cookie

↓

Return Response
```

Notice

Every step exists for a reason.

---

# 3. Why Router Calls AuthService Instead of Repository

One of the first implementation decisions.

Router could directly call

```
MerchantRepository.create()
```

But Signup is not just

```
Create Merchant
```

Signup also performs

- Password Hashing
- Merchant Creation
- Token Generation
- Refresh Session Creation
- Transaction Management

These together form one business operation.

Therefore,

Router delegates the work to

```
AuthService.signup()
```

---

# 4. Why Signup Returns Domain Objects Instead of HTTP Responses

Our Service returns

```
merchant

access_token

refresh_token
```

It does **not** return

```
JSON

Response

Cookie
```

Why?

Because the Service should know nothing about HTTP.

Its responsibility ends when the business operation succeeds.

The Router converts business results into an HTTP response.

---

# 5. Why model_validate() Happens Inside Router

One question we discussed extensively was

> Why doesn't AuthService return MerchantResponse?

Because `MerchantResponse` is a Pydantic model designed for the HTTP layer.

The Service works with domain objects (ORM models).

The Router converts them into Response Models.

```
Merchant ORM

↓

MerchantResponse.model_validate()

↓

JSON
```

This keeps business logic independent from FastAPI.

---

# 6. Why Password Is Hashed Before Persistence

Merchant should never exist with a plain password.

The flow is

```
Plain Password

↓

bcrypt

↓

Merchant ORM

↓

Repository.create()
```

The Repository never receives the plain password.

---

# 7. Why Refresh Token Is Hashed Before Storage

Refresh Tokens are generated,

then immediately hashed.

```
Refresh Token

↓

SHA-256

↓

Database
```

Only the original token is returned to the client.

The database never stores it in plain text.

---

# 8. Why We Use flush() Before Creating Refresh Token

The Refresh Token belongs to a Merchant.

That relationship requires the Merchant's primary key.

At this point,

the Merchant has not been committed yet.

Calling

```
flush()
```

sends the INSERT to PostgreSQL,

allowing SQLAlchemy to populate the generated ID,

while keeping the transaction open.

This allows the Refresh Token to reference the Merchant within the same transaction.

---

# 9. Why There Is Only One commit()

Signup is one business operation.

It creates

- Merchant
- Refresh Session

Both must succeed together.

If either operation fails,

the entire transaction rolls back.

One business operation.

One transaction.

One commit.

---

# 10. Why Tokens Are Generated Before the Response but Used Only After Commit

During implementation we discussed an important edge case.

Suppose the transaction fails.

The client should never receive valid authentication credentials.

Our implementation ensures the HTTP response is only built after the transaction completes successfully.

The Router only sends the Access Token and sets the Refresh Cookie after the Service finishes without error.

---

# 11. Why Access Token Is Returned but Refresh Token Is Not

Access Token

↓

Returned inside JSON

Refresh Token

↓

Stored inside HttpOnly Cookie

The frontend needs direct access to the Access Token for authenticated API requests.

The Refresh Token should remain inaccessible to JavaScript.

---

# 12. Why Router Sets the Cookie

Cookies belong to HTTP.

Therefore,

the Router performs

```
response.set_cookie()
```

instead of the Service.

The Service remains independent of the web framework.

---

# 13. Why Signup Returns the Merchant Instead of Querying Again

After the transaction commits,

SQLAlchemy already has the Merchant object.

There is no need to perform another

```
SELECT Merchant
```

Returning the existing object avoids an unnecessary database query.

---

# 14. Complete Implementation Flow

```
Request

↓

FastAPI Validation

↓

Dependency Injection

↓

Router

↓

AuthService.signup()

↓

Hash Password

↓

MerchantRepository.create()

↓

flush()

↓

Generate Tokens

↓

Hash Refresh Token

↓

RefreshTokenRepository.create()

↓

commit()

↓

Return Merchant + Tokens

↓

Router

↓

model_validate()

↓

response.set_cookie()

↓

SignupResponse

↓

JSON
```

---

# Why We Didn't Choose Other Designs

## Why not let Router call Repository directly?

Because Signup consists of multiple business operations, not just database persistence.

---

## Why not return Response from the Service?

Because Services should remain independent of HTTP.

---

## Why not commit after Merchant creation?

Because Signup should succeed or fail as one business operation.

---

## Why not return ORM objects directly?

Because Response Models control what is exposed to the client.

---

## Why not store Refresh Token directly?

Because database compromise would expose active sessions.

---

# Key Takeaways

✔ Signup is one business operation.

✔ Router handles HTTP.

✔ AuthService handles business logic.

✔ Repository handles persistence.

✔ Passwords are hashed before persistence.

✔ Refresh Tokens are hashed before storage.

✔ One transaction covers the entire Signup process.

✔ Cookies are created only after a successful transaction.

✔ Response Models are built in the Router.

---

# Connection With Our Project

Everything implemented in our Signup API follows one guiding principle:

> **Every layer should do only the work it is responsible for.**

The Router never performs business logic.

The Service never performs HTTP work.

The Repository never decides HTTP responses.

This separation is the reason our Signup implementation remains easy to understand, test, and extend.