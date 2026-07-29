# Payment Gateway Backend
# FastAPI - 03 Error Handling

---

# 1. Purpose of this Document

Every backend system eventually encounters errors.

Examples include:

- Invalid request data
- Duplicate email addresses
- Incorrect passwords
- Expired JWTs
- Database failures
- Unexpected exceptions

Handling these errors consistently is part of designing a reliable backend.

This document explains the error handling strategy used in our Payment Gateway.

Instead of focusing on FastAPI syntax, it explains:

- Which layer should detect errors.
- Which layer should convert them into HTTP responses.
- Which HTTP status codes we use.
- When transactions should rollback.
- How our architecture keeps business logic independent from HTTP.

---

# 2. Errors Can Occur at Different Layers

A request passes through several layers.

```
Client

↓

FastAPI

↓

Router

↓

Service

↓

Repository

↓

Database
```

Errors can occur at any stage.

Each layer should handle only the errors it understands.

---

# 3. Validation Errors

The first layer is FastAPI itself.

Suppose the client sends

```json
{
    "email": "abc"
}
```

but omits

```
password
```

FastAPI never executes our endpoint.

Instead,

Pydantic validation fails.

```
JSON

↓

Pydantic Validation

↓

422 Unprocessable Entity
```

The Router,

Service,

and Repository never run.

---

# 4. Business Errors

Suppose validation succeeds.

Now the Service performs business rules.

Example

```
Signup

↓

Email already exists
```

or

```
Login

↓

Incorrect Password
```

These are not database errors.

They are business errors.

The Service is responsible for detecting them.

---

# 5. Persistence Errors

Sometimes the business logic is correct,

but the database operation fails.

Examples

```
Database Connection Lost

Constraint Violation

Deadlock

Timeout
```

The Repository understands these errors because it interacts directly with SQLAlchemy and PostgreSQL.

---

# 6. Unexpected Errors

Some failures cannot be anticipated.

Examples

```
Programming Bug

Network Failure

Database Crash

Unexpected Exception
```

These eventually become

```
500 Internal Server Error
```

The client knows something failed,

but internal implementation details should never be exposed.

---

# 7. Which Layer Should Raise Errors?

One of the architectural decisions we made was separating responsibilities.

Router

↓

HTTP

Service

↓

Business Rules

Repository

↓

Persistence

Therefore,

each layer should raise different kinds of errors.

---

# 8. Router Responsibility

Router understands HTTP.

It is responsible for

- Request
- Response
- Cookies
- Headers
- HTTP Status Codes

It should never contain business validation.

For example,

Router should not check

```
Email already exists
```

That belongs to the Service.

---

# 9. Service Responsibility

Service owns business logic.

Examples

```
Merchant already exists

↓

Signup not allowed
```

```
Incorrect Password

↓

Authentication Failed
```

The Service decides whether a business operation succeeds.

It does not perform SQL directly.

---

# 10. Repository Responsibility

Repository performs persistence.

Examples

```
INSERT

UPDATE

DELETE

SELECT
```

It should not decide

```
401

404

409
```

Those are HTTP concepts.

Repository should remain independent of FastAPI.

---

# 11. Why Repository Shouldn't Raise HTTPException

Suppose Repository contains

```python
raise HTTPException(...)
```

Now Repository depends on FastAPI.

That creates unnecessary coupling.

Instead,

Repository should expose persistence failures.

Higher layers decide how those failures become HTTP responses.

This keeps Repository reusable outside FastAPI.

---

# 12. Transaction Rollback

Suppose Signup performs

```
Create Merchant

↓

Create Refresh Token

↓

Database Error
```

The Service catches the failure.

```
Rollback

↓

Raise Exception

↓

Return Error
```

The client receives an error,

and no partial data remains.

Rollback belongs to the business transaction,

not to the Router.

---

# 13. HTTP Status Codes Used In Our Project

## 400 Bad Request

The request is syntactically valid,

but logically incorrect.

Example

```
Unsupported Device Type
```

---

## 401 Unauthorized

Authentication failed.

Examples

```
Invalid Password

Expired Access Token

Invalid JWT
```

---

## 403 Forbidden

Authentication succeeded,

but the merchant is not allowed to perform the requested operation.

Example

```
Merchant attempting Admin operation
```

---

## 404 Not Found

Requested resource does not exist.

Example

```
Merchant ID not found

Payment not found
```

---

## 409 Conflict

The request conflicts with existing data.

Example

```
Email already registered
```

This is exactly what our Signup API returns.

---

## 422 Unprocessable Entity

Generated automatically by FastAPI.

Occurs before business logic executes.

Example

```
Missing required fields

Invalid email format
```

---

## 500 Internal Server Error

Unexpected server failure.

The client receives a generic message.

Internal exception details remain inside server logs.

---

# 14. Error Flow During Signup

Successful flow

```
Validate Request

↓

Hash Password

↓

Create Merchant

↓

Create Refresh Token

↓

Commit

↓

Success
```

Failure

```
Validate Request

↓

Create Merchant

↓

Create Refresh Token

↓

Database Error

↓

Rollback

↓

Error Response
```

Notice

No partial merchant remains.

---

# 15. Why Business Logic Shouldn't Know HTTP

Suppose tomorrow

our AuthService is reused by

- FastAPI
- CLI Tool
- Background Worker

Business logic should still work.

If AuthService raises HTTPException directly,

it becomes tightly coupled to FastAPI.

Keeping business logic independent improves reusability.

---

# 16. Complete Error Handling Flow

```
HTTP Request

↓

Validation

↓

Dependency Injection

↓

Router

↓

Service

↓

Repository

↓

Database

↓

Exception

↓

Rollback

↓

Service

↓

Router

↓

HTTP Response
```

Every layer performs only its own responsibility.

---

# Why We Didn't Choose Other Designs

## Why not check everything inside Router?

Because Router should only manage HTTP.

Business rules belong to the Service.

---

## Why not let Repository raise HTTPException?

Because Repository should remain independent of FastAPI.

---

## Why not expose database exceptions directly?

Internal implementation details should never be returned to clients.

---

## Why not commit partial work?

Because every business operation should succeed or fail as a whole.

---

# Key Takeaways

✔ Validation errors are handled by FastAPI before our code executes.

✔ Business errors belong to the Service.

✔ Persistence errors originate from the Repository.

✔ HTTP concerns remain inside the Router.

✔ Transactions rollback when business operations fail.

✔ Internal implementation details should never leak to clients.

---

# Interview Notes

★★★★★ Why shouldn't Repository raise HTTPException?

Because Repository belongs to the persistence layer and should remain independent of FastAPI.

---

★★★★★ What happens if a database error occurs during Signup?

The transaction is rolled back and the client receives an error response.

---

★★★★★ Why does FastAPI return 422 before entering the endpoint?

Because Pydantic validates the request before the endpoint executes.

---

★★★★☆ When should 409 Conflict be used?

When the request conflicts with existing resources, such as attempting to register an email that already exists.

---

★★★★☆ Why keep business logic independent of HTTP?

Because business logic may be reused outside FastAPI, such as background workers or CLI tools.

---

# Connection With Our Project

```
POST /auth/signup

↓

FastAPI Validation

↓

Router

↓

AuthService

↓

MerchantRepository

↓

RefreshTokenRepository

↓

Commit

↓

Success Response
```

If something fails

```
POST /auth/signup

↓

FastAPI Validation

↓

Router

↓

AuthService

↓

MerchantRepository

↓

RefreshTokenRepository

↓

Database Exception

↓

Rollback

↓

Error Response
```

Our error handling follows one simple principle:

- **FastAPI handles validation errors.**
- **The Service handles business errors.**
- **The Repository handles persistence errors.**
- **The Router translates the final outcome into an HTTP response.**