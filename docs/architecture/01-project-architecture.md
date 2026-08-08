# Payment Gateway Backend
# Document 01 - Project Architecture

---

# 1. Purpose of this Document

This document explains the architecture of our backend project.

It is **not** intended to explain FastAPI syntax or SQLAlchemy APIs. Instead, it answers questions like:

- Why do we have Routers?
- Why do we have Services?
- Why do we have Repositories?
- Why are some things classes while others are just functions?
- Why is business logic separated from database logic?
- How do different components communicate?

Understanding this document means understanding **how the entire backend is organized**.

---

# 2. High-Level Architecture

Our backend follows a layered architecture.

```

                Client
                   │
                   ▼
          ┌────────────────┐
          │     Router     │
          └────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │    Service     │
          └────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Repository    │
          └────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ SQLAlchemy ORM │
          └────────────────┘
                   │
                   ▼
             PostgreSQL


Every layer has one responsibility.

A layer should never perform the responsibility of another layer.

This makes the project easier to maintain, test and extend.

3. Router Layer
Responsibility

The Router represents the HTTP layer.

Its responsibility is to communicate with the outside world.

It should answer questions like:

What URL should this endpoint have?
Is this a POST or GET request?
What request schema is expected?
What response schema should be returned?
Should cookies be attached?
What HTTP status should be returned?

It should not contain business logic.

Example:

@router.post(
    "/signup",
    response_model=SignupResponse
)

The router knows:

this is POST
URL is /signup
response must follow SignupResponse

But it should not decide whether an email already exists.

That belongs to the Service layer.

4. Service Layer

The Service layer is the heart of the application.

Almost every important decision is taken here.

Examples:

Can this merchant sign up?
Does this email already exist?
Should password be hashed?
Should refresh token be generated?
Should JWT be created?

These are business rules.

Why doesn't Router do this?

Imagine tomorrow we want:

REST API
GraphQL API
CLI
Background worker

All of them need signup logic.

If signup logic lived inside Router, we'd have to duplicate it.

Instead:


REST API
│
├──────────► AuthService.signup()

GraphQL
│
├──────────► AuthService.signup()

Background Job
│
└──────────► AuthService.signup()


Business logic lives only once.

5. Repository Layer

The Repository layer is responsible for Persistence.

What is Persistence?

Persistence simply means:

Making data survive after the program stops.

If Python stores

merchant = Merchant(...)

inside RAM,

it disappears once the application stops.

If Repository stores it in PostgreSQL,

it survives.

That is called persistence.

Repository Responsibilities

Repository should only know:

How to save data.
How to retrieve data.
How to update data.
How to delete data.

Repository should NOT know:

Signup rules
Login rules
JWT
Password hashing

Those belong to Service.

Think of Repository as:

"Database translator."

The service says:


Create this merchant.


Repository translates that into SQL.

6. Why Service Shouldn't Write SQL

Suppose AuthService contained SQL directly.


SELECT * FROM merchant WHERE email = ...


Now business logic and database logic become mixed.

Problems:

Hard to read
Hard to test
Hard to change database technology

Instead:


AuthService

↓

merchant_repository.get_by_email(...)

↓

Repository

↓

SQLAlchemy

↓

PostgreSQL


Every layer focuses on its own job.

7. Components vs Utilities (Very Important)

This is one of the most important Low-Level Design concepts.

Component

A Component represents a part of the application.

Examples:


AuthService

MerchantRepository

PaymentService

RefundService


Notice these represent business modules.

They own state, responsibilities and collaborate with other components.

They are usually implemented as classes.

Utility

Utilities don't represent a business module.

They perform reusable work.

Examples:

hash_password()

verify_password()

generate_uuid()

hash_token()

They don't need internal state.

Therefore they are simple functions.

Rule

Ask yourself:

"Does this represent a business component?"

If YES

→ create a class.

If NO

→ create a function.

This simple rule avoids unnecessary classes.

8. Why AuthService is a Class

AuthService represents authentication.

Authentication is a business capability.

It performs multiple related operations.


signup()

login()

logout()

refresh_token()


All of these belong to the same business concept.

Therefore they naturally belong inside one class.

9. Merchant Responsibilities vs Auth Responsibilities

This distinction is extremely important.

Merchant is an Entity.

It represents data.


merchant_id

business_name

email

status

password


It should not know how to login.

AuthService represents authentication.

Responsibilities:

verify password
hash password
generate JWT
create refresh token
validate credentials

Notice:

AuthService uses Merchant.

Merchant does NOT know about AuthService.

Dependency direction:


AuthService
│
│ uses
▼
Merchant


Never the opposite.

10. Communication Flow (Signup)

Client

│

▼

Router

│

▼

AuthService

│

├─────────────► MerchantRepository

│

├─────────────► JWT Utility

│

├─────────────► Password Utility

│

└─────────────► RefreshTokenRepository


Notice:

AuthService orchestrates everything.

Repositories never call each other.

Utilities never call repositories.

Router never accesses database directly.

11. Why This Architecture Scales

Suppose tomorrow we add:

Google Login
OAuth
Apple Login

Only AuthService changes.

Repository barely changes.

Router barely changes.

Good architecture isolates change.

That is the real purpose of layered architecture.

Key Takeaways

✔ Router handles HTTP.

✔ Service handles business rules.

✔ Repository handles persistence.

✔ Utilities perform reusable work.

✔ Components represent business capabilities.

✔ Service coordinates components.

✔ Repository never contains business logic.

✔ Router never talks directly to database.

Interview Notes
Q1. Why use Service Layer?

Because business logic should not depend on HTTP.

Q2. What is Persistence?

Making data survive beyond application execution.

Q3. Why Repository Pattern?

To separate business logic from database implementation.

Q4. When should you create a class?

When representing a business component.

Q5. When should you create a function?

When the logic is stateless and reusable.

Connection with Our Project

Router

↓

auth.py

↓

AuthService

↓

MerchantRepository

↓

SQLAlchemy

↓

PostgreSQL

Utilities:

hash_password()
verify_password()
create_access_token()
hash_token()

Components:

AuthService
MerchantRepository
RefreshTokenRepository

---

## I deliberately did **not** include:

- `Depends()`
- `APIRouter`
- `response_model`
- `Response`
- `HTTPException`
- `Pydantic`

because those belong to the next document:

> **02-fastapi-request-lifecycle.md**

That document will answer **every "how does FastAPI know..." question** you've asked over the last few days, including:
- how FastAPI inspects function signatures,
- where `return` goes,
- the difference between `response_model` and `Response`,
- how `Depends(get_db)` works internally,
- how `yield` is used,
- request/response serialization,
- and how FastAPI handles both expected (`HTTPException`) and unexpected (`500`) errors.

Keeping those concepts separate makes each document focused and easier to revisit later.