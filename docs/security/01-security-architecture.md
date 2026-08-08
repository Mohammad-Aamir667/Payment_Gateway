# Payment Gateway Backend
# Security - 01 Security Architecture

---

# 1. Purpose of this Document

Security is not just about encryption, hashing, or JWTs.

Security starts with architectural decisions.

This document explains **why our authentication system is designed the way it is.**

Instead of explaining security concepts in isolation, we answer questions that came up while building this project.

- Why don't we use Sessions?
- Why do we have Access Tokens and Refresh Tokens?
- Why is the Access Token returned in JSON?
- Why is the Refresh Token stored inside an HttpOnly Cookie?
- Why is the Refresh Token stored in the database?
- Why is the Refresh Token hashed?
- Why are responsibilities divided between Router, Service and Utilities?

This document explains the overall security architecture.

Individual implementation details are covered in later documents.

---

# 2. Our Authentication Architecture

Our authentication system consists of five components.

```
                    Client
                       │
                       │
             Login / Signup
                       │
                       ▼
                  AuthService
         ┌──────────┼───────────┐
         │          │           │
         ▼          ▼           ▼
 Password Utility JWT Utility Refresh Token Repository
         │                      │
         └──────────────┬───────┘
                        ▼
                  PostgreSQL
```

Notice something.

There is **no single component responsible for security.**

Security is achieved by combining multiple small responsibilities.

---

# 3. Authentication vs Authorization

One of the most common confusions.

Authentication answers

> Who are you?

Example

```
Email

Password
```

↓

Merchant verified

Authorization answers

> What are you allowed to do?

Example

```
Merchant

↓

Can create payment?

Can issue refund?

Can view settlements?
```

Our current project primarily focuses on **Authentication**.

Authorization will grow as more APIs are added.

---

# 4. Why We Chose JWT Instead of Server Sessions

One of the first architectural decisions.

Traditional applications store user sessions on the server.

```
Browser

↓

Session ID

↓

Server Memory
```

Instead,

our payment gateway stores authentication inside JWT.

```
Browser

↓

JWT

↓

Stateless Authentication
```

Why?

Because payment gateways often need to scale horizontally.

Any server should be able to verify a JWT without asking another server for session data.

This keeps authentication stateless.

---

# 5. Why One JWT Wasn't Enough

Initially it seems simple.

```
Login

↓

Generate JWT

↓

Done
```

But suppose JWT expires in 15 minutes.

The merchant now has to log in every 15 minutes.

Terrible user experience.

Instead we separated responsibilities.

```
Access Token

↓

Short Lifetime

↓

API Authentication
```

and

```
Refresh Token

↓

Long Lifetime

↓

Create New Access Tokens
```

Each token has one responsibility.

---

# 6. Why Access Token is Short-Lived

Suppose an attacker steals an Access Token.

If it expires in

```
15 minutes
```

the attack window is small.

Even if the attacker cannot be stopped immediately,

the stolen token becomes useless quickly.

Short-lived credentials reduce risk.

---

# 7. Why Refresh Token Exists

Refresh Token solves one problem.

```
Access Token Expired

↓

Don't force Login Again

↓

Issue New Access Token
```

The merchant continues working without entering credentials repeatedly.

This improves usability while keeping Access Tokens short-lived.

---

# 8. Why Access Token is Returned in JSON

During development you asked:

> "If Refresh Token goes into a Cookie, why doesn't Access Token?"

The answer lies in how they are used.

Frontend needs the Access Token for every API request.

```
Authorization

↓

Bearer <Access Token>
```

JavaScript must be able to read it.

Therefore,

it is returned inside the response body.

```
{
    "access_token": "..."
}
```

---

# 9. Why Refresh Token Goes into HttpOnly Cookie

Refresh Token has a different purpose.

It should almost never be touched by JavaScript.

Instead,

the browser stores it automatically.

```
Browser

↓

HttpOnly Cookie

↓

Sent Automatically

↓

Refresh Endpoint
```

Because JavaScript cannot access HttpOnly Cookies,

XSS attacks become much less damaging.

---

# 10. Why Refresh Tokens Are Stored in Database

This question came up multiple times while building the project.

JWT is stateless.

So why store anything?

Because Refresh Tokens represent active sessions.

We want to support

- Logout
- Device Management
- Session Revocation
- Future Token Rotation

Without storing Refresh Tokens,

none of these become possible.

Database storage gives us control over active sessions.

---

# 11. Why Refresh Tokens Are Hashed

During implementation,

we discovered bcrypt's 72-byte limitation.

That led us to redesign Refresh Token storage.

Instead of

```
Plain Refresh Token
```

we store

```
SHA256(Refresh Token)
```

Why?

Suppose someone steals our database.

If Refresh Tokens were stored directly,

every active session would immediately be compromised.

Hashing protects those sessions.

Unlike passwords,

Refresh Tokens are already cryptographically random,

so SHA-256 is sufficient for lookup and protection.

---

# 12. Why Passwords Use bcrypt Instead of SHA-256

Passwords are different.

Users choose passwords.

Humans create predictable passwords.

```
password123

admin123

qwerty
```

Attackers know this.

bcrypt intentionally slows down hashing,

making brute-force attacks significantly more expensive.

Therefore,

Passwords use bcrypt.

Refresh Tokens use SHA-256.

Different data.

Different threats.

Different solutions.

---

# 13. Security Responsibilities

One important design decision was dividing responsibilities.

## Router

Responsible for

- HTTP
- Cookies
- Responses

Never verifies passwords.

Never generates JWT.

---

## AuthService

Responsible for

- Login
- Signup
- Authentication Decisions
- Coordinating Components

Never performs SQL directly.

---

## Password Utility

Responsible only for

```
hash_password()

verify_password()
```

---

## JWT Utility

Responsible only for

```
create_access_token()

decode_token()
```

---

## Refresh Token Repository

Responsible only for

```
Store Token Hash

Find Token

Delete Token
```

Notice

Every component has one responsibility.

This reduces security mistakes.

---

# 14. Complete Security Flow

```
Merchant Login

↓

Verify Password

↓

Generate Access Token

↓

Generate Refresh Token

↓

Hash Refresh Token

↓

Store Hash

↓

Return Access Token

↓

Set Refresh Cookie
```

Later

```
Access Token Expires

↓

Browser sends Refresh Cookie

↓

Validate Refresh Token

↓

Issue New Access Token
```

---

# 15. Why This Architecture Scales

Suppose tomorrow we introduce

- Multiple Devices
- Token Rotation
- Admin Session Revocation
- Remember Me
- Login History

Our architecture already supports these features.

We don't need to redesign authentication.

Good architecture anticipates future growth without making today's implementation unnecessarily complex.

---

# Why We Didn't Choose Other Designs

## Why not Server Sessions?

Because JWT allows stateless authentication and horizontal scalability.

---

## Why not One Long-Lived JWT?

Because stolen tokens would remain usable for a long time.

---

## Why not Store Plain Refresh Tokens?

Because database compromise would expose every active session.

---

## Why not Store Access Tokens in Database?

Because Access Tokens are stateless and intentionally short-lived.

---

## Why not Put Access Token Inside HttpOnly Cookie?

Because our frontend needs to explicitly send it in the `Authorization: Bearer` header for authenticated API requests.

---

# Key Takeaways

✔ Authentication and Authorization are different concerns.

✔ Access Tokens and Refresh Tokens solve different problems.

✔ Access Tokens are short-lived and returned in JSON.

✔ Refresh Tokens are long-lived and stored in HttpOnly Cookies.

✔ Refresh Tokens are stored as SHA-256 hashes.

✔ Passwords are hashed using bcrypt.

✔ Security responsibilities are divided across multiple components.

✔ Stateless authentication improves scalability while Refresh Token storage provides session control.

---

# Interview Notes

★★★★★ Why use Access Token + Refresh Token instead of one JWT?

Because Access Tokens can remain short-lived for security while Refresh Tokens provide a seamless user experience by issuing new Access Tokens.

---

★★★★★ Why store Refresh Tokens in the database?

To support logout, session revocation, device management, and future token rotation.

---

★★★★★ Why hash Refresh Tokens but not Access Tokens?

Refresh Tokens are stored in the database and must remain protected if the database is compromised. Access Tokens are not stored by the server.

---

★★★★☆ Why use bcrypt for passwords but SHA-256 for Refresh Tokens?

Passwords are human-generated and require slow hashing to resist brute-force attacks. Refresh Tokens are cryptographically random, so a fast hash is sufficient for secure lookup.

---

★★★★☆ Why is the Refresh Token stored in an HttpOnly Cookie?

To prevent JavaScript from reading long-lived credentials, reducing the impact of XSS attacks.

---

# Connection With Our Project

```
POST /auth/signup

↓

AuthService

↓

Hash Password (bcrypt)

↓

Create Merchant

↓

Generate Access Token

↓

Generate Refresh Token

↓

Hash Refresh Token (SHA-256)

↓

Store Refresh Token Hash

↓

Commit

↓

Router

↓

Set HttpOnly Refresh Cookie

↓

Return Access Token
```

This architecture separates responsibilities clearly:

- **Router** handles HTTP.
- **AuthService** makes authentication decisions.
- **Utilities** perform cryptographic operations.
- **Repositories** manage persistence.

Security is therefore achieved through **well-defined responsibilities**, not by placing all security logic in one component.