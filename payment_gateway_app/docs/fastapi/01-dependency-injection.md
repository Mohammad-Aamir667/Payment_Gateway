# Payment Gateway Backend
# FastAPI - 01 Dependency Injection

---

# 1. Purpose of this Document

Dependency Injection (DI) is one of FastAPI's core features.

However, it is often misunderstood as simply "passing objects into functions."

That is only part of the story.

This document explains how Dependency Injection works in **our Payment Gateway**.

It answers questions like:

- Why do we use `Depends()`?
- What actually happens when FastAPI sees `Depends(get_db)`?
- Why don't we manually create database sessions?
- Why does `get_db()` use `yield` instead of `return`?
- How does FastAPI know what to inject?
- Who closes the database session?
- Why does this architecture improve scalability and testing?

---

# 2. What Problem Does Dependency Injection Solve?

Imagine our Signup API without Dependency Injection.

```python
@router.post("/signup")
def signup(request: SignupRequest):

    db = SessionLocal()

    auth_service = AuthService(db)

    result = auth_service.signup(request)

    db.close()

    return result
```

Every API endpoint would repeat the same code.

- Create Session
- Create Service
- Close Session

As the project grows,

this repetition becomes difficult to maintain.

Dependency Injection removes this responsibility from our API endpoints.

---

# 3. Our Signup API

Instead of manually creating everything,

our endpoint looks like this.

```python
@router.post("/signup")
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):
    ...
```

Notice something.

We never call

```python
get_db()
```

ourselves.

FastAPI does it automatically.

---

# 4. What Does Depends() Mean?

Many beginners think

```python
Depends(get_db)
```

means

```
Call this function.
```

Not exactly.

It actually tells FastAPI

> "Before executing this endpoint, resolve this dependency and provide its result."

It is an instruction,

not a normal function call.

---

# 5. What Happens Behind the Scenes?

Suppose a request arrives.

```
POST /auth/signup
```

FastAPI first inspects the endpoint.

```python
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
)
```

FastAPI notices

```
Depends(get_db)
```

Before calling `signup()`,

it performs

```
get_db()

↓

Receive Session

↓

Call signup(db)
```

The endpoint never creates the Session itself.

---

# 6. What Does get_db() Do?

Our dependency looks like

```python
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
```

Notice

It does not return immediately.

Instead,

it pauses at

```
yield
```

FastAPI receives the Session,

uses it,

then resumes the function after the request finishes.

---

# 7. Why yield Instead of return?

This was one of the most important questions we discussed.

Suppose we wrote

```python
return db
```

After returning,

the function is finished.

It has no opportunity to execute cleanup code.

With

```python
yield
```

execution pauses.

```
Create Session

↓

Yield Session

↓

Endpoint Executes

↓

Resume Function

↓

Close Session
```

This allows FastAPI to automatically clean up resources.

---

# 8. Session Lifecycle

For every incoming request,

FastAPI performs

```
Create Session

↓

Inject Session

↓

Execute Endpoint

↓

Close Session
```

Every request receives its own Session.

Sessions are never shared across requests.

This prevents accidental data leakage and transaction conflicts.

---

# 9. What Happens Internally?

Conceptually,

FastAPI behaves like this.

```python
generator = get_db()

db = next(generator)

try:

    signup(db)

finally:

    generator.close()
```

We never write this ourselves.

FastAPI performs it automatically.

---

# 10. How Does FastAPI Know What to Inject?

FastAPI first inspects the endpoint's function signature.

```
SignupRequest

↓

Parse Request Body
```

```
Depends(get_db)

↓

Resolve Dependency
```

```
Response

↓

Prepare HTTP Response
```

FastAPI understands the endpoint simply by reading its parameters.

---

# 11. Dependency Chain

Dependencies can depend on other dependencies.

Example

```
get_current_merchant()

↓

Depends(get_db)

↓

Session
```

Flow

```
Request

↓

get_db()

↓

Database Session

↓

get_current_merchant()

↓

Merchant

↓

Endpoint
```

FastAPI resolves dependencies recursively.

---

# 12. Why Router Doesn't Create Session

Our Router has one responsibility.

```
HTTP
```

It should never worry about

- Session creation
- Session cleanup
- Database lifecycle

Those responsibilities belong to Dependency Injection.

The Router simply receives a ready-to-use Session.

---

# 13. Why Repository Doesn't Create Session

Suppose Repository created its own Session.

```
MerchantRepository

↓

SessionLocal()

↓

commit()
```

Now every repository would have its own independent transaction.

This breaks the transaction boundary we designed earlier.

Instead,

the Service shares one Session across all repositories.

```
Router

↓

Dependency Injection

↓

One Session

↓

AuthService

↓

MerchantRepository

↓

RefreshRepository
```

All repositories participate in the same transaction.

---

# 14. Dependency Injection Improves Testing

Suppose we want to test Signup.

Without DI,

Signup always creates a real database Session.

Testing becomes difficult.

With DI,

we simply inject another dependency.

```
Production

↓

Real Database
```

```
Testing

↓

Test Database

or

Mock Session
```

The endpoint code never changes.

Only the dependency changes.

---

# 15. Why Dependency Injection Improves Architecture

Notice what each layer knows.

Router

↓

Receives Session

Service

↓

Uses Session

Repository

↓

Executes Queries

No layer is responsible for creating Sessions.

Dependency creation is separated from business logic.

This follows the Dependency Inversion Principle.

---

# 16. Complete Request Flow

```
HTTP Request

↓

FastAPI

↓

Inspect Function Signature

↓

Resolve Depends(get_db)

↓

Create Session

↓

Inject Session

↓

Router

↓

AuthService

↓

Repositories

↓

Commit / Rollback

↓

Return Response

↓

Resume get_db()

↓

Close Session
```

The Session exists only for the lifetime of one request.

---

# Why We Didn't Choose Other Designs

## Why not call SessionLocal() inside every endpoint?

Because every endpoint would repeat the same boilerplate and become responsible for resource management.

---

## Why not let Repository create Sessions?

Because multiple repositories must participate in the same transaction.

Creating independent Sessions would break transaction boundaries.

---

## Why not use return instead of yield?

Because `yield` allows FastAPI to execute cleanup code after the endpoint finishes.

---

## Why not use one global Session?

Database Sessions are not thread-safe.

Each request must receive its own Session.

---

# Key Takeaways

✔ Dependency Injection separates object creation from object usage.

✔ FastAPI resolves dependencies before executing the endpoint.

✔ `Depends()` is an instruction, not a normal function call.

✔ `yield` allows automatic resource cleanup.

✔ Every request receives its own Session.

✔ All repositories share the same injected Session.

✔ The Router never manages Session creation or cleanup.

✔ Dependency Injection makes testing significantly easier.

---

# Interview Notes

★★★★★ What problem does Dependency Injection solve?

It separates dependency creation from business logic, reducing boilerplate and improving maintainability.

---

★★★★★ Why does `get_db()` use `yield` instead of `return`?

Because `yield` allows FastAPI to perform cleanup after the request finishes, ensuring database Sessions are always closed.

---

★★★★★ How does FastAPI know to call `get_db()`?

FastAPI inspects the endpoint's function signature. When it finds `Depends(get_db)`, it resolves that dependency before executing the endpoint.

---

★★★★☆ Why shouldn't Repositories create their own Sessions?

Because a business operation may involve multiple repositories. Sharing one injected Session ensures they all participate in the same transaction.

---

★★★★☆ Why does each request receive its own Session?

Database Sessions are not thread-safe and represent the state of a single unit of work. Sharing Sessions across requests could lead to transaction conflicts and inconsistent state.

---

# Connection With Our Project

```
POST /auth/signup

↓

FastAPI

↓

Inspect Endpoint Signature

↓

Depends(get_db)

↓

Create SQLAlchemy Session

↓

Inject Session

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

Return Response

↓

FastAPI Resumes get_db()

↓

db.close()
```

The important idea is this:

Our business logic never creates database Sessions.

FastAPI's Dependency Injection creates them, injects them where needed, and guarantees they are cleaned up after every request.

This keeps our architecture clean, consistent, and scalable.