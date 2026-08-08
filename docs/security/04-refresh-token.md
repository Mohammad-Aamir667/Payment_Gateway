# Payment Gateway Backend
# Security - 04 Refresh Token

---

# 1. Purpose of this Document

Refresh Tokens are one of the most misunderstood parts of JWT authentication.

Many people think they simply "generate new Access Tokens."

In reality, they solve several important architectural problems.

This document explains the design decisions we made while building our authentication system.

It answers questions like:

- Why do Refresh Tokens exist?
- Why aren't long-lived Access Tokens enough?
- Why do we store Refresh Tokens in the database?
- Why do we hash Refresh Tokens?
- Why don't we use bcrypt?
- Why are Refresh Tokens stored inside HttpOnly Cookies?
- How does Logout work?
- How can we support multiple devices?
- How can this architecture evolve to Refresh Token Rotation?

---

# 2. Why Refresh Tokens Exist

Suppose our authentication system only had Access Tokens.

```
Merchant Login

↓

Access Token (15 Minutes)

↓

Expired

↓

Login Again
```

The merchant would need to enter credentials repeatedly.

This creates a poor user experience.

Instead,

we introduced Refresh Tokens.

```
Merchant Login

↓

Access Token

+

Refresh Token
```

The Access Token handles authentication.

The Refresh Token maintains the session.

Each token has one responsibility.

---

# 3. Why Not Use One Long-Lived Access Token?

At first glance,

this seems simpler.

```
Login

↓

Access Token

↓

Valid for 30 Days
```

But suppose the token is stolen.

The attacker now has access for an entire month.

Instead,

our design separates concerns.

```
Access Token

↓

Short Lifetime

↓

Authentication
```

```
Refresh Token

↓

Long Lifetime

↓

Issue New Access Tokens
```

This reduces the attack window while maintaining usability.

---

# 4. Why Refresh Tokens Are Stored in Database

During development we repeatedly discussed this question.

If JWT is stateless,

why store anything?

Because Refresh Tokens represent **active login sessions**.

They allow us to control those sessions.

Database storage enables:

- Logout
- Device-specific sessions
- Session revocation
- Future token rotation
- Session expiration
- Login history (future)

Without storing Refresh Tokens,

the server would have no control after issuing them.

---

# 5. Why Access Tokens Aren't Stored

Notice the difference.

Access Token

```
Stateless

↓

Verified using Signature
```

Refresh Token

```
Stateful

↓

Verified using Database
```

This is intentional.

The server only stores long-lived credentials.

Short-lived credentials remain stateless.

---

# 6. Why Refresh Tokens Are Hashed

Suppose we stored

```
Plain Refresh Token
```

inside the database.

If someone steals the database,

they immediately gain access to every active session.

Instead,

our flow is

```
Refresh Token

↓

SHA-256

↓

Database
```

The original Refresh Token never gets stored.

Only its hash.

---

# 7. Why We Chose SHA-256 Instead of bcrypt

This decision came directly from our implementation.

Initially,

it seems logical to reuse bcrypt.

However,

we discovered bcrypt only considers the first **72 bytes** of input.

Refresh Tokens are long,

cryptographically random strings.

bcrypt would ignore everything after 72 bytes.

That makes it unsuitable.

Instead,

we use

```
SHA-256
```

Why?

Because Refresh Tokens are already random.

They do not require slow hashing.

We only need

- deterministic hashing
- fast lookup
- protection if the database is compromised

SHA-256 satisfies all three.

---

# 8. Why Refresh Tokens Are Stored in HttpOnly Cookies

One question we discussed during implementation was

> Why isn't the Refresh Token returned in JSON like the Access Token?

Because JavaScript should never need to access it.

Instead,

the browser stores it automatically.

```
Server

↓

Set-Cookie

↓

Browser

↓

HttpOnly Cookie
```

Whenever the Refresh endpoint is called,

the browser automatically includes the cookie.

JavaScript never reads the token directly.

---

# 9. Why HttpOnly Matters

Suppose an attacker injects JavaScript using an XSS vulnerability.

If Refresh Tokens were stored in JavaScript-accessible storage,

the attacker could steal them.

With HttpOnly,

```
JavaScript

↓

Cannot Read Cookie
```

The browser still sends the cookie,

but scripts cannot access its value.

This significantly reduces the impact of XSS attacks.

---

# 10. Refresh Token Lifecycle

```
Merchant Login

↓

Generate Refresh Token

↓

SHA-256

↓

Store Hash

↓

Set HttpOnly Cookie

↓

Browser Stores Cookie
```

Later,

```
Access Token Expires

↓

Browser Calls /refresh

↓

Cookie Sent Automatically

↓

Hash Cookie Value

↓

Find Matching Hash

↓

Generate New Access Token

↓

Return Access Token
```

Notice

The Refresh Token is only used when necessary.

---

# 11. Logout Flow

Logout is one reason we store Refresh Tokens.

```
Logout Request

↓

Read Refresh Cookie

↓

SHA-256

↓

Find Session

↓

Delete Session

↓

Clear Cookie

↓

Success
```

After deletion,

that Refresh Token becomes unusable.

Even if someone still possesses it,

the server no longer recognizes it.

---

# 12. Supporting Multiple Devices

Because Refresh Tokens are stored in the database,

each login creates its own session.

Example

```
Laptop

↓

Refresh Token A
```

```
Mobile

↓

Refresh Token B
```

```
Tablet

↓

Refresh Token C
```

Each device has its own independent session.

Logging out from one device does not affect the others.

---

# 13. Future Refresh Token Rotation

Although not implemented yet,

our architecture supports Refresh Token Rotation.

Current

```
Refresh Token

↓

Generate Access Token
```

Future

```
Refresh Token

↓

Validate

↓

Generate New Refresh Token

↓

Delete Old Token

↓

Store New Hash

↓

Return New Cookie
```

If an attacker steals an old Refresh Token,

it becomes useless once rotation occurs.

---

# 14. Refresh Token Repository

The repository has one responsibility.

```
Create Refresh Session

Find Refresh Session

Delete Refresh Session
```

It does not

- verify passwords
- generate JWT
- set cookies
- build HTTP responses

Keeping responsibilities separate makes the authentication system easier to maintain.

---

# 15. Security Responsibilities

AuthService

↓

Generate Refresh Token

↓

Hash Refresh Token

↓

Repository Stores Hash

↓

Router Sets Cookie

Each layer performs exactly one responsibility.

---

# Why We Didn't Choose Other Designs

## Why not store plain Refresh Tokens?

Because database compromise would expose every active session.

---

## Why not use bcrypt?

Because Refresh Tokens are already random and bcrypt ignores input beyond 72 bytes.

SHA-256 provides deterministic hashing suitable for lookup.

---

## Why not store Refresh Token in Local Storage?

Because JavaScript can read Local Storage.

HttpOnly Cookies reduce the impact of XSS attacks.

---

## Why not keep only Access Tokens?

Because users would need to log in every time the Access Token expires.

---

## Why not make Access Tokens long-lived?

Because stolen credentials would remain valid for much longer.

---

# Key Takeaways

✔ Refresh Tokens maintain user sessions.

✔ Refresh Tokens are stored in the database.

✔ Only SHA-256 hashes are stored.

✔ Refresh Tokens are stored inside HttpOnly Cookies.

✔ Logout works by deleting the stored Refresh Token hash.

✔ Each device can maintain its own Refresh Token.

✔ The architecture supports future Refresh Token Rotation.

---

# Interview Notes

★★★★★ Why store Refresh Tokens in the database?

To support logout, session revocation, multiple devices, and future token rotation.

---

★★★★★ Why hash Refresh Tokens?

To protect active sessions if the database is compromised.

---

★★★★★ Why use SHA-256 instead of bcrypt?

Refresh Tokens are already cryptographically random and require deterministic hashing for database lookup. bcrypt's 72-byte input limitation also makes it unsuitable.

---

★★★★☆ Why use HttpOnly Cookies?

Because JavaScript cannot read them, reducing the impact of XSS attacks.

---

★★★★☆ Why aren't Access Tokens stored in the database?

Because Access Tokens are stateless and verified using their digital signature.

---

# Connection With Our Project

```
POST /auth/login

↓

Verify Password

↓

Generate Access Token

↓

Generate Refresh Token

↓

SHA-256(Refresh Token)

↓

RefreshTokenRepository.create()

↓

Commit

↓

Router

↓

response.set_cookie(HttpOnly)

↓

Return Access Token
```

Later,

```
POST /auth/refresh

↓

Browser Sends Refresh Cookie

↓

SHA-256(Cookie Value)

↓

Find Matching Refresh Session

↓

Generate New Access Token

↓

Return Access Token
```

Finally,

```
POST /auth/logout

↓

Browser Sends Refresh Cookie

↓

SHA-256(Cookie Value)

↓

RefreshTokenRepository.delete()

↓

Commit

↓

Router Clears Cookie

↓

Logout Successful
```

Our Refresh Token architecture follows one core principle:

- **Access Tokens provide fast, stateless authentication.**
- **Refresh Tokens provide controlled, stateful session management.**

By separating these responsibilities, we achieve both scalability and security without compromising the user experience.