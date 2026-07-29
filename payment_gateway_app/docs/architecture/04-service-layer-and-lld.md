# Payment Gateway Backend
# Document 04 - Service Layer & Low-Level Design (LLD)

---

# 1. Purpose of this Document

As our backend grows, it becomes impossible to write everything inside one file.

This document explains:

- Why we created a Service Layer
- What Low-Level Design (LLD) means
- Why some things are classes and others are functions
- How responsibilities are divided
- How components collaborate
- How to think like a backend engineer instead of just writing code

This document uses our Payment Gateway project as the reference.

---

# 2. What is Low-Level Design (LLD)?

Low-Level Design is the process of deciding **how individual components of an application should be organized and interact**.

It answers questions like:

- What classes should exist?
- What should each class be responsible for?
- Which class talks to which?
- Which functions belong together?
- How should data flow through the application?

LLD is **not about writing code first**.

It is about organizing code so that it remains understandable even after thousands of lines are added.

---

# 3. The Biggest Mistake Beginners Make

Many beginners write code like this:

```python
signup():

    validate_email()

    hash_password()

    insert_merchant()

    generate_jwt()

    insert_refresh_token()

    send_email()

    create_audit_log()
```

Everything works.

But one year later,

signup() becomes 600 lines long.

Nobody knows what it is responsible for anymore.

The problem is not that the code is wrong.

The problem is that **one function owns too many responsibilities.**

---

# 4. The Core Principle of LLD

Every component should have **one clear responsibility.**

Think of a company.

CEO

↓

HR

↓

Finance

↓

Engineering

↓

Legal

Everyone has a different responsibility.

Imagine if HR also handled accounting.

Or Finance also hired employees.

The company would become chaotic.

Software is no different.

---

# 5. Service Layer

The Service Layer represents the application's **business capabilities**.

Examples in our project:

```
AuthService

PaymentService

RefundService

MerchantService
```

Notice something.

These names describe **business operations**.

Not database tables.

Not HTTP endpoints.

Business capabilities.

---

# 6. Why AuthService Exists

Authentication is not one operation.

Authentication includes

- Signup
- Login
- Logout
- Refresh Token
- Password Verification

These operations are related.

Instead of scattering them across different files,

we group them together.

```python
class AuthService:

    signup()

    login()

    logout()

    refresh()
```

The class now represents

"Everything related to Authentication."

---

# 7. Why Not Just Write Functions?

This was one of the questions we discussed several times.

Suppose we write

```python
signup()

login()

logout()

refresh()
```

as unrelated functions.

Technically,

they work perfectly.

So why create a class?

Because a class represents a **business component**, not just executable code.

Think of it this way.

Functions answer

> "How do I perform one task?"

Classes answer

> "What part of my application owns these tasks?"

AuthService is not created because Python requires it.

It is created because Authentication is a business concept.

---

# 8. Components vs Utilities

This is one of the most useful design rules.

## Components

Components represent business modules.

Examples

```
AuthService

MerchantRepository

PaymentService

RefundService
```

Components collaborate with each other.

They usually become classes.

---

## Utilities

Utilities perform reusable work.

Examples

```python
hash_password()

verify_password()

generate_uuid()

hash_token()
```

These do not represent business concepts.

They simply perform reusable operations.

Therefore,

they remain module-level functions.

---

# Rule

Ask one question.

> "Does this represent a business capability?"

If yes

↓

Class

If no

↓

Function

---

# 9. Repository is NOT Business Logic

Suppose we need

```python
merchant_repository.create()
```

Repository knows

- INSERT
- UPDATE
- DELETE
- SELECT

It does not know

- Signup
- Login
- JWT
- Passwords

That is intentional.

Repository speaks

"Database."

Service speaks

"Business."

---

# 10. Service is an Orchestrator

One of the best ways to understand Service Layer is this.

Imagine an orchestra.

There are

- violin
- piano
- drums
- guitar

The conductor does not play every instrument.

Instead,

the conductor coordinates everyone.

Service Layer behaves exactly the same.

```
AuthService

│

├────────► MerchantRepository

├────────► JWT Utility

├────────► Password Utility

└────────► RefreshTokenRepository
```

Notice

AuthService performs almost no low-level work itself.

It coordinates other components.

This is called **Orchestration**.

---

# 11. Data Flow

Signup follows this path.

```
Router

↓

AuthService

↓

MerchantRepository

↓

Database

↓

MerchantRepository

↓

AuthService

↓

RefreshTokenRepository

↓

Router

↓

Client
```

Each layer performs only its own responsibility.

Nobody skips layers.

---

# 12. Why Router Shouldn't Call Repository

Suppose Router directly writes

```python
merchant_repository.create(...)
```

Now Router knows

- HTTP
- Database

Tomorrow we add

- email verification
- audit logging
- token generation

Router becomes full of business logic.

Instead

Router only says

```python
auth_service.signup(...)
```

The Router doesn't care how signup works.

That is exactly how it should be.

---

# 13. Why Repository Shouldn't Call Another Repository

Imagine

```
MerchantRepository

↓

RefreshTokenRepository

↓

AuditRepository

↓

EmailRepository
```

Now repositories begin depending on each other.

Soon,

database code becomes impossible to understand.

Instead,

Repositories remain independent.

Only the Service coordinates them.

---

# 14. Dependency Direction

Our project follows this dependency flow.

```
Router

↓

Service

↓

Repository

↓

Database
```

Notice

Dependencies only move downward.

Repository never calls Router.

Database never calls Service.

This keeps the architecture simple.

---

# 15. Why This Makes Testing Easier

Suppose we want to test

AuthService.

We don't care about FastAPI.

We don't care about HTTP.

We only verify

```
signup()

↓

merchant created

↓

refresh token stored

↓

JWT generated
```

Because responsibilities are separated,

each layer can be tested independently.

---

# 16. Our Current Architecture

```
Client

↓

FastAPI Router

↓

AuthService

├────────► MerchantRepository

├────────► RefreshTokenRepository

├────────► Password Utility

└────────► JWT Utility

↓

PostgreSQL
```

Notice

Every arrow represents one dependency.

Every dependency has a clear purpose.

---

# 17. Future Growth

Tomorrow we may add

PaymentService.

```
PaymentService

├────────► PaymentRepository

├────────► MerchantRepository

├────────► NotificationService

└────────► AuditService
```

Notice

Nothing in AuthService changes.

This is good design.

Each business capability grows independently.

---

# Key Takeaways

✔ LLD is about organizing software before writing code.

✔ Service Layer represents business capabilities.

✔ Repository represents persistence.

✔ Utilities perform reusable operations.

✔ Components are usually classes.

✔ Utilities are usually functions.

✔ Service coordinates multiple components.

✔ Repository never contains business logic.

✔ Router never coordinates business operations.

✔ Dependencies always move downward.

---

# Interview Notes

### What is the responsibility of the Service Layer?

To implement business logic and coordinate multiple components.

---

### Why use a Repository Pattern?

To separate persistence from business logic.

---

### Why create AuthService as a class?

Because Authentication is a business capability that owns multiple related operations.

---

### When should you create a class?

When representing a business component with related responsibilities.

---

### When should you create a function?

When the logic is stateless, reusable, and does not represent a business concept.

---

# Connection With Our Project

Router

↓

AuthService.signup()

↓

MerchantRepository.create()

↓

RefreshTokenRepository.create()

↓

Return business objects

↓

Router creates HTTP response

Our architecture is therefore divided into four responsibilities:

- HTTP Layer → Router
- Business Layer → Services
- Persistence Layer → Repositories
- Infrastructure Layer → Utilities (JWT, Password Hashing, UUID, etc.)

Each layer has exactly one primary responsibility, making the system easier to understand, extend, and test.