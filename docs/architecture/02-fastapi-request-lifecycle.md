# Payment Gateway Backend
# Document 02 - FastAPI Request Lifecycle

---

# 1. Purpose of this Document

In the previous document, we learned about the architecture of our project.

This document explains **how FastAPI executes one HTTP request from start to finish**.

Instead of memorizing FastAPI syntax, our goal is to answer:

- How does FastAPI know what data our function expects?
- What is Dependency Injection?
- Why does `Depends(get_db)` work?
- Why does `get_db()` use `yield` instead of `return`?
- What is `response_model`?
- What is the `Response` object?
- Where does `return` actually go?
- How does FastAPI convert Python objects into JSON?
- How does FastAPI handle errors?

Throughout this document we will use our **Signup API** as the running example.

---

# 2. The Journey of One HTTP Request

Suppose the frontend sends

POST /auth/signup

with

```json
{
    "business_name": "Flipkart",
    "email": "flipkart@example.com",
    "password": "password123",
    "device_identifier": "WEB"
}
```

The complete lifecycle looks like this.

```

Client
│
│ HTTP Request
▼
FastAPI
│
│ Find matching route
▼
Router Function
│
│ Validate Request
▼
Dependency Injection
│
▼
Service Layer
│
▼
Repository Layer
│
▼
Database
│
▼
Repository returns
│
▼
Service returns
│
▼
Router returns
│
▼
FastAPI Serializes Response
│
▼
HTTP Response
│
▼
Client

```

Notice something important.

Our application code only runs in the middle.

FastAPI controls everything before and after.

---

# 3. How FastAPI Knows Which Function to Call

Suppose we have

```python
@router.post("/signup")
def signup(...):
```

When the application starts,

FastAPI scans every router.

It builds something similar to

```

POST /auth/signup
↓

signup()

```

This is called **Route Registration**.

Later,

when an HTTP request arrives,

FastAPI simply looks up

```

POST /auth/signup

```

and immediately knows

```

Call signup()

```

---

# 4. Understanding APIRouter

Think of APIRouter as a **small collection of related endpoints**.

Example

```

Auth Router

signup()

login()

logout()

refresh()

```

Every

```python
@router.post(...)
```

registers itself inside this router.

Nothing is attached to the application yet.

Only when we write

```python
app.include_router(auth_router)
```

does FastAPI copy all those routes into the main application.

So,

APIRouter is simply an organizational tool.

It helps us split a large application into smaller modules.

---

# 5. How FastAPI Knows What Data signup() Needs

Our signup function looks like

```python
def signup(
    request: MerchantSignupRequest,
    response: Response,
    db: Session = Depends(get_db),
):
```

Notice something.

We never tell FastAPI

"Read JSON."

or

"Create Response."

or

"Call get_db."

FastAPI figures it out by **inspecting the function signature**.

This is one of the biggest strengths of FastAPI.

---

## Parameter 1

```python
request: MerchantSignupRequest
```

FastAPI sees

```

Pydantic Model

```

It immediately understands

> Read JSON body.

It then creates

```python
MerchantSignupRequest(...)
```

using the incoming JSON.

If validation fails,

our function is never called.

FastAPI automatically returns

```

422 Unprocessable Entity

```

---

## Parameter 2

```python
response: Response
```

FastAPI recognizes

```

Starlette Response Object

```

It creates one.

Then passes it into our function.

This object allows us to modify

- cookies
- headers
- status code

Notice

it is **NOT** the response body.

---

## Parameter 3

```python
db: Session = Depends(get_db)
```

FastAPI recognizes

```

Dependency

```

Before calling signup,

it executes

```python
get_db()
```

The yielded object becomes

```python
db
```

inside our function.

---

# 6. Understanding Depends()

This is FastAPI's Dependency Injection system.

Instead of writing

```python
db = SessionLocal()
```

inside every endpoint,

we centralize database creation.

```python
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
```

Now every endpoint simply writes

```python
db: Session = Depends(get_db)
```

FastAPI performs approximately

```python
generator = get_db()

db = next(generator)

signup(db=db)

generator.close()
```

Notice

We never call

```python
get_db()
```

FastAPI does.

---

# 7. Why use yield instead of return?

This is pure Python.

A function using

```python
yield
```

becomes a generator.

Unlike return,

execution pauses at

```python
yield db
```

FastAPI uses the yielded Session.

After the request completes,

execution continues.

```python
finally:

    db.close()
```

runs automatically.

That guarantees

- one Session per request
- automatic cleanup
- no leaked database connections

---

# 8. What happens inside signup()?

After all dependencies are ready,

FastAPI finally calls

```python
signup(
    request=request,
    response=response,
    db=db,
)
```

Now our own application starts running.

Inside signup

we

- call AuthService
- set refresh cookie
- return SignupResponse

Everything else has already been prepared by FastAPI.

---

# 9. What does return actually return to?

Many beginners think

```

return

↓

Response object

```

This is incorrect.

The return value goes back to **FastAPI**.

```

signup()

↓

return SignupResponse(...)

↓

FastAPI

↓

JSON Serialization

↓

HTTP Response

↓

Browser

```

Think of FastAPI as the caller.

Just like

```python
x = add()
```

receives the return value,

FastAPI receives

```python
SignupResponse(...)
```

---

# 10. Response Object vs response_model

These two are often confused.

## Response

```python
response: Response
```

Represents the actual HTTP response.

It allows us to modify

- Cookies
- Headers
- Status Code

Example

```python
response.set_cookie(...)
```

---

## response_model

```python
@router.post(
    response_model=SignupResponse
)
```

This tells FastAPI

> Whatever this function returns,

convert it into

```

SignupResponse

```

It has three responsibilities.

- Validation
- Serialization
- Filtering unwanted fields

Suppose we accidentally return

```python
{
    "merchant": merchant,
    "access_token": "...",
    "password": "abc"
}
```

FastAPI removes

```

password

```

because it isn't part of SignupResponse.

This is an important security feature.

---

# 11. How FastAPI Converts Objects into JSON

Our Service returns

```python
SignupResponse(...)
```

FastAPI now

- validates it
- converts it into JSON
- sends it to the client

This process is called **Serialization**.

The reverse process,

where JSON becomes Python objects,

is called **Deserialization**.

---

# 12. Why do we return Access Token in JSON?

The frontend needs it.

JavaScript receives

```json
{
    "access_token": "..."
}
```

Later,

every request becomes

```

Authorization: Bearer <token>

```

Therefore,

the frontend must be able to read it.

---

## Why not Refresh Token?

Refresh Tokens are long-lived credentials.

If JavaScript could read them,

an XSS attack could steal them.

Instead,

we attach them using

```python
response.set_cookie(
    httponly=True
)
```

HttpOnly cookies cannot be accessed through JavaScript.

This greatly improves security.

---

# 13. Error Handling

FastAPI distinguishes two kinds of errors.

## Expected Errors

Examples

- Email already exists
- Invalid credentials
- Merchant not found

These are part of business logic.

We intentionally write

```python
raise HTTPException(
    status_code=409,
    detail="Email already exists"
)
```

FastAPI catches it.

Returns

```json
{
    "detail":"Email already exists"
}
```

The application continues running.

---

## Unexpected Errors

Examples

- Database unavailable
- Programming bug
- AttributeError
- TypeError

We don't intentionally raise these.

FastAPI catches them.

Returns

```

500 Internal Server Error

```

while logging the exception.

Later,

our project can define global exception handlers

to log errors in a consistent way.

---

# 14. Putting Everything Together

The Signup request travels through the application like this.

```

Client

│

▼

FastAPI

│

▼

Route Matching

│

▼

Request Validation (Pydantic)

│

▼

Dependency Injection

│

├── Response Object

│

└── Database Session

│

▼

signup()

│

▼

AuthService

│

▼

Repositories

│

▼

PostgreSQL

│

▼

AuthService returns

│

▼

signup() returns SignupResponse

│

▼

FastAPI

│

├── Validate response_model

├── Serialize JSON

├── Attach Cookies

└── Send HTTP Response

│

▼

Client

```

---

# Key Takeaways

✔ FastAPI inspects the function signature to understand what an endpoint needs.

✔ Pydantic models represent request and response contracts.

✔ `Depends()` is FastAPI's Dependency Injection mechanism.

✔ `yield` allows FastAPI to automatically clean up resources.

✔ `Response` modifies headers, cookies and status codes.

✔ `response_model` defines the structure of the JSON body.

✔ The return value goes back to FastAPI, not to the `Response` object.

✔ FastAPI serializes Python objects into JSON before sending them to the client.

✔ `HTTPException` represents expected request failures.

✔ Unexpected exceptions become HTTP 500 responses.

---

# Interview Notes

### Why does FastAPI use Dependency Injection?

To centralize object creation and make components reusable.

---

### Difference between Response and response_model?

Response modifies HTTP metadata.

response_model defines the response body.

---

### Why use yield inside get_db()?

To automatically release the database session after the request finishes.

---

### Why is response_model important?

It validates, serializes and filters the outgoing response.

---

### What does FastAPI inspect to understand an endpoint?

The function signature and type annotations.