# Payment Gateway Backend
# Security - 03 JWT (JSON Web Token)

---

# 1. Purpose of this Document

JWT (JSON Web Token) is the mechanism our Payment Gateway uses for authenticating API requests.

This document does **not** explain the JWT specification or cryptography in detail.

Instead, it explains the architectural decisions we made while implementing authentication.

It answers questions like:

- Why did we choose JWT?
- Why is JWT stateless?
- Why don't we store Access Tokens in the database?
- Why is the Access Token returned in JSON?
- Why is it short-lived?
- What information should a JWT contain?
- What information should never be stored inside a JWT?
- Why is JWT signed but not encrypted?

---

# 2. What Role Does JWT Play?

JWT is **proof of authentication**.

After Login or Signup,

the server verifies the merchant's identity.

Once verified,

the server creates a JWT.

```
Merchant

↓

Verified

↓

Generate JWT

↓

Return to Client
```

The client presents this JWT on every authenticated request.

The server does not ask for the password again.

---

# 3. Why Did We Choose JWT?

One of our earliest authentication decisions was choosing between

```
Server Sessions
```

and

```
JWT
```

We chose JWT because it is **stateless**.

Once generated,

every API server can verify the token independently.

```
Client

↓

Authorization Header

↓

Any API Server

↓

Verify Signature

↓

Authenticated
```

No shared server-side session storage is required.

This makes horizontal scaling much simpler.

---

# 4. Why JWT is Stateless

This is probably the biggest advantage of JWT.

Suppose the merchant sends

```
Authorization:

Bearer eyJhbGci...
```

The server verifies

- Signature
- Expiration
- Claims

If everything is valid,

the request is authenticated.

Notice

The server never asks

```
Database

↓

Does this Access Token exist?
```

It already has everything it needs inside the token.

That is why JWT authentication is called **stateless**.

---

# 5. Why We Don't Store Access Tokens

During implementation we discussed this question multiple times.

If JWT is authentication,

why don't we store it?

Because storing every Access Token would remove one of JWT's biggest advantages.

Instead of

```
Client

↓

Database Lookup

↓

Authentication
```

our flow becomes

```
Client

↓

Verify Signature

↓

Authentication
```

Authentication becomes much faster because there is no database lookup.

---

# 6. Why Access Tokens Expire Quickly

Suppose someone steals an Access Token.

If it remains valid for

```
30 days
```

the attacker has access for an entire month.

Instead,

our Access Token expires quickly.

```
15 Minutes
```

or whatever expiration policy we configure.

A stolen Access Token becomes useless after a short time.

Short-lived credentials reduce risk.

---

# 7. Why Refresh Tokens Exist

If Access Tokens expire frequently,

the merchant would otherwise need to log in repeatedly.

Instead,

the Refresh Token performs only one job.

```
Access Token Expired

↓

Refresh Token

↓

Issue New Access Token
```

Authentication remains secure,

while user experience remains smooth.

---

# 8. What Information Should a JWT Contain?

During our API design,

we intentionally kept the payload small.

Example

```json
{
    "merchant_id": "...",
    "email": "...",
    "exp": 1721300000
}
```

Only information needed for authentication should be included.

---

# 9. What Should Never Be Stored in JWT?

A JWT should not become a database record.

Avoid storing

- Business Name
- GST Number
- Address
- Phone Number
- Preferences
- Large Objects

Why?

Because JWT is sent with every authenticated request.

Larger payloads increase request size and expose unnecessary information.

JWT should contain only authentication-related claims.

---

# 10. Why JWT is Signed Instead of Encrypted

One question we discussed was

> Can anyone read a JWT?

Yes.

JWT is **Base64 encoded**, not encrypted.

Anyone holding the token can decode the payload.

Example

```
Header

Payload

Signature
```

The payload is visible.

The security comes from the **Signature**.

If someone changes

```
merchant_id
```

or

```
email
```

the signature becomes invalid.

The server immediately rejects the token.

JWT protects against **modification**, not reading.

---

# 11. Why Return JWT in JSON

During implementation you asked

> Why don't we store Access Token inside HttpOnly Cookie?

Because the frontend actively uses the Access Token.

Every authenticated request includes

```
Authorization:

Bearer <Access Token>
```

JavaScript must be able to read it.

Therefore,

our Login and Signup APIs return

```json
{
    "access_token": "..."
}
```

The frontend decides how it wants to manage that token.

---

# 12. JWT Verification

Whenever an authenticated API is called,

our backend performs

```
Receive JWT

↓

Verify Signature

↓

Verify Expiration

↓

Extract Claims

↓

Merchant Authenticated
```

Only after successful verification does the request proceed.

---

# 13. JWT Lifecycle

```
Merchant Login

↓

Verify Password

↓

Generate JWT

↓

Return Access Token

↓

Frontend Stores Token

↓

API Request

↓

Authorization Header

↓

Verify JWT

↓

Merchant Authenticated
```

Notice

Passwords are only used once.

JWT performs authentication afterward.

---

# 14. Security Responsibilities

JWT Utility has one responsibility.

```
Generate Access Token

Verify Access Token
```

It does **not**

- Query database
- Verify password
- Set cookies
- Build HTTP responses

Those responsibilities belong elsewhere.

This keeps the utility focused and reusable.

---

# Why We Didn't Choose Other Designs

## Why not Server Sessions?

Because JWT enables stateless authentication and horizontal scalability.

---

## Why not Long-Lived Access Tokens?

Because stolen tokens would remain usable for a long time.

Short-lived tokens reduce the attack window.

---

## Why not Store Access Tokens in Database?

Because JWT is intentionally stateless.

Database lookups would remove one of its biggest advantages.

---

## Why not Put Business Information Inside JWT?

JWT is transmitted with every authenticated request.

Only authentication claims should be included.

---

## Why not Return Access Token in HttpOnly Cookie?

Because the frontend needs to attach the Access Token to the `Authorization` header for API requests.

---

# Key Takeaways

✔ JWT represents successful authentication.

✔ Access Tokens are stateless.

✔ Access Tokens are never stored in the database.

✔ JWT contains only authentication claims.

✔ JWT is signed, not encrypted.

✔ Access Tokens are intentionally short-lived.

✔ The frontend sends JWT using the Authorization header.

✔ Refresh Tokens solve the problem of Access Token expiration.

---

# Interview Notes

★★★★★ Why use JWT instead of Server Sessions?

JWT enables stateless authentication, allowing any server to verify the token without shared session storage.

---

★★★★★ Why don't we store Access Tokens?

Because JWT already contains the required authentication information and can be verified using its signature.

---

★★★★★ Why should JWT payload remain small?

Because it is transmitted with every authenticated request and should contain only authentication-related information.

---

★★★★☆ Is JWT encrypted?

No.

JWT is Base64 encoded and digitally signed.

Anyone can decode the payload, but nobody can modify it without invalidating the signature.

---

★★★★☆ Why are Access Tokens short-lived?

To minimize the impact of stolen credentials.

---

# Connection With Our Project

```
POST /auth/login

↓

Verify Password

↓

JWT Utility

↓

Generate Access Token

↓

Return Access Token (JSON)

↓

Frontend Stores Token

↓

GET /payments

↓

Authorization: Bearer <Access Token>

↓

JWT Utility

↓

Verify Signature

↓

Merchant Authenticated
```

Our JWT architecture follows a simple principle:

- **Passwords prove identity once.**
- **JWT proves identity for subsequent requests.**
- **Refresh Tokens maintain the session without requiring repeated logins.**