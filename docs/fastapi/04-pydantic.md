# Payment Gateway Backend
# FastAPI - 04 Pydantic

---

# 1. Purpose of this Document

Pydantic is one of the most important libraries in FastAPI.

However, Pydantic is much more than validation.

Throughout our project, we used Pydantic for

- Request Validation
- Response Serialization
- Type Conversion
- Data Validation
- ORM Conversion

This document explains how we use Pydantic in our Payment Gateway.

---

# 2. Where Do We Use Pydantic?

Our project uses Pydantic in three places.

```
Incoming Request

↓

Request Model

↓

Business Logic

↓

Response Model

↓

JSON Response
```

Notice

Pydantic appears before and after the business logic.

---

# 3. Request Models

Suppose the client sends

```json
{
    "business_name": "ABC Pvt Ltd",
    "email": "abc@example.com",
    "password": "Password123"
}
```

FastAPI converts it into

```python
MerchantSignupRequest
```

Our Service never receives raw JSON.

It receives a strongly typed Python object.

---

# 4. Why Request Models?

Without Pydantic

```
dict

↓

request["email"]

↓

KeyError?
```

With Pydantic

```
request.email
```

Cleaner.

Safer.

Type checked.

---

# 5. Validation Happens Automatically

Suppose

```
email missing
```

FastAPI performs

```
JSON

↓

Pydantic

↓

Validation

↓

422
```

Our endpoint never executes.

This is one of FastAPI's biggest advantages.

---

# 6. Response Models

After Signup,

our Service returns

```
Merchant ORM
```

The client should never receive an ORM object.

Instead

```
Merchant ORM

↓

MerchantResponse

↓

JSON
```

---

# 7. Why We Don't Return ORM Objects

Merchant contains

```
password

refresh_tokens

internal fields

relationships
```

The client should not see these.

Instead

```python
MerchantResponse
```

contains only

```
merchant_id

business_name

email

created_at
```

Pydantic controls exactly what leaves our application.

---

# 8. model_validate()

This was one of the biggest questions during implementation.

Suppose we have

```python
merchant
```

This is a SQLAlchemy object.

We convert it using

```python
MerchantResponse.model_validate(
    merchant
)
```

Pydantic reads

```
merchant.email

merchant.business_name

merchant.created_at
```

and creates

```
MerchantResponse
```

---

# 9. Why from_attributes=True?

Normally,

Pydantic expects

```
Dictionary
```

Example

```python
{
    "email": "...",
    "business_name": "..."
}
```

Our ORM object is different.

```
merchant.email

merchant.business_name
```

Instead of dictionary keys,

values come from object attributes.

Therefore,

our Response Model contains

```python
model_config = ConfigDict(
    from_attributes=True
)
```

Without this,

`model_validate()` would fail for ORM objects.

---

# 10. Why Password Isn't Returned

Merchant ORM

```
merchant.password
```

exists.

MerchantResponse

```
password
```

does not.

Pydantic only serializes declared fields.

Everything else is ignored.

This protects sensitive data.

---

# 11. Serialization

Suppose Router returns

```python
SignupResponse(...)
```

FastAPI performs

```
Pydantic Object

↓

Dictionary

↓

JSON

↓

HTTP Response
```

This process is called

Serialization.

---

# 12. Deserialization

Incoming Request

```
JSON

↓

MerchantSignupRequest
```

This is

Deserialization.

---

# 13. Nested Models

Our Signup Response contains

```
Merchant

+

Access Token
```

Instead of

```
Dictionary inside Dictionary
```

we define

```python
SignupResponse

↓

MerchantResponse

↓

Access Token
```

Each model validates its own data.

---

# 14. Optional Fields

Some fields are optional.

Example

```
phone

website

logo
```

Pydantic allows

```
None
```

without validation failure.

---

# 15. Why Pydantic Improves Architecture

Without Pydantic,

every Router would manually

- validate
- parse
- convert
- serialize

With Pydantic

```
JSON

↓

Python Objects

↓

Business Logic

↓

Python Objects

↓

JSON
```

Most of this becomes automatic.

---

# 16. Complete Flow

```
Client

↓

JSON

↓

MerchantSignupRequest

↓

Router

↓

AuthService

↓

Repository

↓

Merchant ORM

↓

MerchantResponse

↓

SignupResponse

↓

JSON

↓

Client
```

Notice

Objects change throughout the request.

---

# Why We Didn't Choose Other Designs

## Why not use dictionaries everywhere?

Because dictionaries provide no validation and poor type safety.

---

## Why not return ORM objects?

Because ORM models contain internal implementation details.

---

## Why not manually build JSON?

FastAPI automatically serializes Pydantic models.

---

## Why not expose password?

Because Response Models explicitly define what leaves the application.

---

# Key Takeaways

✔ Pydantic validates incoming requests.

✔ Pydantic serializes outgoing responses.

✔ Request Models convert JSON into Python objects.

✔ Response Models convert Python objects into JSON.

✔ model_validate() converts ORM objects into Pydantic models.

✔ from_attributes=True allows Pydantic to read SQLAlchemy objects.

✔ Response Models protect sensitive fields.

---

# Interview Notes

★★★★★ Why use Pydantic Request Models?

To validate incoming requests and convert JSON into strongly typed Python objects.

---

★★★★★ Why use Response Models?

To control exactly what data is returned to clients.

---

★★★★★ Why use model_validate()?

To convert ORM objects into Pydantic models.

---

★★★★☆ Why is from_attributes=True required?

Because SQLAlchemy objects expose attributes instead of dictionary keys.

---

★★★★☆ Why doesn't the password appear in the response?

Because it is not declared in the Response Model.

---

# Connection With Our Project

```
POST /auth/signup

↓

JSON Request

↓

MerchantSignupRequest

↓

Router

↓

AuthService

↓

MerchantRepository

↓

Merchant ORM

↓

MerchantResponse.model_validate()

↓

SignupResponse

↓

JSON Response
```

The important idea is this:

Pydantic acts as the **boundary** between the outside world and our application.

- Incoming JSON becomes validated Python objects.
- Outgoing Python objects become safe, structured JSON.