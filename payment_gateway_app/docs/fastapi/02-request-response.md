# Payment Gateway Backend
# FastAPI - 02 Request & Response Lifecycle

---

# 1. Purpose of this Document

Every API begins with an HTTP Request and ends with an HTTP Response.

Between these two events, many components work together.

While implementing our Signup API, we discussed questions like:

- What happens after the client sends JSON?
- Who validates the request?
- Who creates the Merchant object?
- Who converts ORM objects into JSON?
- Why do we use Pydantic?
- Why doesn't the password appear in the response?
- Where is the Refresh Cookie created?

This document explains the complete lifecycle of a request in our project.

---

# 2. High-Level Flow

Whenever a client calls

```
POST /auth/signup
```

the request follows this path.

```
Client

↓

FastAPI

↓

Route Matching

↓

Request Validation

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

Repository

↓

Service

↓

Response Model

↓

JSON Serialization

↓

HTTP Response
```

Every layer has one responsibility.

---

# 3. Client Sends HTTP Request

Suppose the frontend sends

```http
POST /auth/signup
```

Request Body

```json
{
    "business_name": "ABC Pvt Ltd",
    "email": "abc@example.com",
    "password": "Password@123"
}
```

At this point,

FastAPI has only received raw HTTP data.

Nothing has been validated yet.

---

# 4. Route Matching

FastAPI first determines

```
Which endpoint should handle this request?
```

It searches registered routes.

```
POST

/auth/signup
```

↓

Matches

```python
@router.post("/signup")
```

Only after finding the correct endpoint does FastAPI continue.

---

# 5. Request Validation

Suppose our endpoint looks like

```python
def signup(
    request: MerchantSignupRequest
)
```

FastAPI notices

```
MerchantSignupRequest
```

It automatically performs

```
JSON

↓

Pydantic

↓

MerchantSignupRequest Object
```

If validation fails,

the endpoint never executes.

Instead,

FastAPI returns

```
422 Unprocessable Entity
```

---

# 6. Dependency Resolution

Before executing the endpoint,

FastAPI resolves

```python
Depends(get_db)
```

Flow

```
Create Session

↓

Inject Session

↓

Call Endpoint
```

The Router receives a ready-to-use Session.

---

# 7. Router

Now our endpoint finally executes.

The Router's responsibilities are

- Receive validated request
- Receive dependencies
- Call Service
- Build HTTP Response

Notice

The Router does **not**

- Hash passwords
- Generate JWT
- Write SQL

Those responsibilities belong elsewhere.

---

# 8. Service Layer

AuthService performs the business operation.

```
Validate Business Rules

↓

Hash Password

↓

Generate Tokens

↓

Call Repositories

↓

Commit
```

The Service knows nothing about HTTP.

It simply performs the Signup operation.

---

# 9. Repository

Repositories translate business operations into database operations.

```
Merchant Object

↓

INSERT

↓

PostgreSQL
```

Repository returns ORM objects,

not JSON.

---

# 10. Database

PostgreSQL performs

```
INSERT Merchant

↓

Generate IDs

↓

Generate Timestamps

↓

Commit
```

Repository receives the ORM object.

---

# 11. Returning from Repository

The flow now reverses.

```
Database

↓

Repository

↓

Service

↓

Router
```

The Router receives

```python
merchant
```

This is still a SQLAlchemy object.

It cannot be returned directly.

---

# 12. Why We Use model_validate()

One question we discussed during Signup implementation was

> Why don't we return the ORM object directly?

Suppose Merchant contains

```
password

refresh_tokens

internal_fields
```

Returning the ORM object would expose implementation details.

Instead,

we convert it.

```python
MerchantResponse.model_validate(merchant)
```

Pydantic reads only the fields defined inside

```
MerchantResponse
```

Everything else is ignored.

---

# 13. Why Password Isn't Returned

Our ORM model contains

```
password
```

Our Response Model does not.

```
Merchant ORM

↓

Pydantic Response Model

↓

JSON
```

Only declared fields are serialized.

Sensitive fields remain hidden.

This is one of the reasons we use Response Models.

---

# 14. Building SignupResponse

Router creates

```python
SignupResponse(
    merchant=merchant_response,
    access_token=access_token
)
```

Notice

Refresh Token is not included.

We deliberately chose another mechanism.

---

# 15. Setting Refresh Cookie

After Service succeeds,

Router performs

```python
response.set_cookie(...)
```

This is important.

Cookies belong to

```
HTTP Layer
```

The Service should never know

- cookies
- headers
- HTTP responses

Those responsibilities remain inside the Router.

---

# 16. Response Serialization

FastAPI now converts

```python
SignupResponse
```

into JSON.

```
Pydantic Object

↓

Dictionary

↓

JSON

↓

HTTP Response
```

The client never receives Python objects.

Only JSON.

---

# 17. Complete Request Lifecycle

```
Client

↓

HTTP Request

↓

FastAPI

↓

Route Matching

↓

Pydantic Validation

↓

Dependency Injection

↓

Router

↓

AuthService

↓

Repositories

↓

Database

↓

Repository

↓

Service

↓

MerchantResponse.model_validate()

↓

SignupResponse

↓

response.set_cookie()

↓

JSON Serialization

↓

HTTP Response
```

Everything we built follows this flow.

---

# Why We Didn't Choose Other Designs

## Why not parse JSON manually?

FastAPI automatically converts JSON into Pydantic models.

Manual parsing would duplicate framework functionality.

---

## Why not return ORM objects?

ORM objects contain internal implementation details.

Response Models expose only the fields intended for clients.

---

## Why not let Service build HTTP responses?

Services implement business logic.

HTTP responses belong to the Router.

---

## Why not let Repository return JSON?

Repositories deal with persistence.

Serialization belongs to FastAPI and Pydantic.

---

## Why not set cookies inside Service?

Cookies are part of HTTP.

The Service should remain independent of the transport layer.

---

# Key Takeaways

✔ FastAPI automatically matches routes.

✔ Pydantic validates requests before the endpoint executes.

✔ Dependency Injection creates required objects.

✔ Router handles HTTP concerns.

✔ Service performs business logic.

✔ Repository performs persistence.

✔ Response Models protect sensitive fields.

✔ FastAPI serializes Pydantic models into JSON automatically.

---

# Interview Notes

★★★★★ What happens before a FastAPI endpoint executes?

FastAPI matches the route, validates the request, resolves dependencies, and only then calls the endpoint.

---

★★★★★ Why use Pydantic Response Models?

To serialize only the intended fields and prevent sensitive data from being exposed.

---

★★★★★ Why doesn't the password appear in the response?

Because it is not part of the Response Model.

Pydantic only serializes declared fields.

---

★★★★☆ Why is `response.set_cookie()` called inside the Router?

Because cookies are part of the HTTP layer, not business logic.

---

★★★★☆ Why shouldn't Repositories return JSON?

Repositories work with ORM objects and database operations.

Serialization belongs to FastAPI and Pydantic.

---

# Connection With Our Project

```
POST /auth/signup

↓

FastAPI

↓

MerchantSignupRequest

↓

Depends(get_db)

↓

Router

↓

AuthService.signup()

↓

MerchantRepository.create()

↓

RefreshTokenRepository.create()

↓

Commit

↓

MerchantResponse.model_validate()

↓

SignupResponse

↓

response.set_cookie(HttpOnly Refresh Token)

↓

JSON Response

↓

Client
```

The important idea is this:

A request is transformed step by step:

```
HTTP

↓

Python Objects

↓

Business Logic

↓

Database

↓

Business Objects

↓

Pydantic Models

↓

JSON

↓

HTTP Response
```

Every layer performs exactly one responsibility, making the entire request lifecycle predictable, maintainable, and easy to reason about.