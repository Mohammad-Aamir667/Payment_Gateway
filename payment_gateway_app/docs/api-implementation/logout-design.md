# Logout API Design

## Overview

At first glance, the Logout API appears to be one of the simplest authentication APIs to implement. Unlike Login or Signup, it neither creates nor retrieves any business data. However, designing a robust logout mechanism involves several important software engineering concepts beyond simply removing a session.

While implementing this API, several architectural decisions had to be made regarding:

- API contract design
- Idempotency
- JWT validation
- Utility function design
- Exception handling
- Repository responsibilities
- Session lifecycle
- Reusability
- Separation of concerns

Although the implementation consists of only a few lines of code, the reasoning behind those lines is significant.

---

# API Flow

```
Client
    │
    ▼
Extract Refresh Token Cookie
    │
    ▼
Verify JWT
    │
    ▼
Hash Refresh Token
    │
    ▼
Repository Lookup
    │
    ▼
Soft Revoke Session
    │
    ▼
Commit Transaction
    │
    ▼
Clear Cookie
    │
    ▼
Return Success Response
```

---

# Why Logout Uses Refresh Token

The access token is intentionally short-lived and is designed only to authorize API requests.

A refresh token, on the other hand, represents an authenticated session.

Since logging out means terminating a session rather than simply invalidating an access token, the Refresh Token becomes the natural identifier for the session.

This also allows a user to remain logged in on multiple devices independently.

```
Laptop
    │
    ├── Refresh Token A

Phone
    │
    ├── Refresh Token B

Desktop
    │
    └── Refresh Token C
```

Logging out from one device should only revoke that particular refresh token.

---

# Idempotency

One of the most important design principles of this API is **idempotency**.

An idempotent API guarantees that performing the same operation multiple times produces the same final state.

Example:

```
Logout

↓

200 OK
```

Calling Logout again

```
Logout

↓

200 OK
```

Calling it again

```
Logout

↓

200 OK
```

The user remains logged out regardless of how many times the endpoint is invoked.

Because of this property, the Logout API intentionally returns success even when:

- the session has already been revoked
- the session no longer exists

The desired state ("no active session") has already been achieved.

---

# Soft Revocation Instead of Deletion

Instead of deleting refresh token records, the project uses soft revocation.

Database schema:

```
created_at

expires_at

revoked_at
```

During logout:

```
revoked_at = current_timestamp
```

instead of

```
DELETE FROM refresh_tokens
```

Advantages:

- Preserves login history
- Helps during security investigations
- Useful for audit logs
- Enables future analytics
- Allows administrators to inspect previous sessions

Deleting rows permanently removes valuable historical information.

---

# Session Lifecycle

```
Login

↓

Refresh Token Created

↓

Session Active

↓

Logout

↓

revoked_at populated

↓

Session Revoked
```

Notice that **expires_at** is never modified during logout.

```
created_at
```

indicates when the session started.

```
expires_at
```

indicates when the session naturally expires.

```
revoked_at
```

indicates when the user explicitly terminated the session.

Keeping these timestamps independent provides a complete picture of the session lifecycle.

---

# Utility Function Design

One of the most important architectural decisions was keeping the JWT utility independent from business logic.

The responsibility of the utility function is:

```
Verify JWT
```

Its responsibility is **not**:

- Login
- Logout
- Refresh
- Authorization
- Business decisions

This follows the Single Responsibility Principle.

```
JWT Utility

↓

Cryptographic Validation
```

Business services decide what should happen after validation.

---

# Designing verify_token()

Instead of creating multiple verification functions, the project uses a single reusable utility.

```python
verify_token(
    token,
    verify_exp=True,
)
```

This utility is reused across multiple APIs.

Protected APIs

```
verify_exp=True
```

Refresh API

```
verify_exp=True
```

Logout API

```
verify_exp=False
```

Only the business rule changes.

The verification logic remains centralized.

---

# Why verify_exp=False During Logout

Normally, JWT verification performs several checks.

```
Decode JWT

↓

Verify Signature

↓

Verify Secret

↓

Verify Algorithm

↓

Verify Expiration

↓

Return Payload
```

During Logout:

```
Decode JWT

↓

Verify Signature

↓

Verify Secret

↓

Verify Algorithm

↓

Skip Expiration Check

↓

Return Payload
```

Passing

```python
options={
    "verify_exp": False
}
```

does **not** disable JWT verification.

It only disables expiration validation.

The token must still:

- have a valid structure
- contain a valid signature
- be signed with the correct secret
- use the expected algorithm

Only the expiration timestamp is ignored.

---

# Why Ignore Expiration During Logout

Logout is different from authentication.

Consider these scenarios.

Valid refresh token

```
Logout

↓

Session Revoked

↓

200 OK
```

Expired refresh token

```
Logout

↓

Session Already Unusable

↓

200 OK
```

Already revoked token

```
Logout

↓

Session Already Revoked

↓

200 OK
```

Session not found

```
Logout

↓

No Active Session

↓

200 OK
```

In every case, the desired final state is identical:

```
No active authenticated session.
```

Ignoring expiration allows the API to preserve idempotency while still validating the authenticity of the token.

---

# Exception Handling Inside PyJWT

An important discovery during implementation was understanding how JWT libraries report errors.

The decode function does **not** return:

```python
False
```

Instead, it raises specific exceptions.

Examples:

```
ExpiredSignatureError
```

```
InvalidSignatureError
```

```
DecodeError
```

```
InvalidAlgorithmError
```

Python automatically transfers control to the matching `except` block.

Example:

```python
try:
    jwt.decode(...)

except ExpiredSignatureError:
    ...

except PyJWTError:
    ...
```

If the token has expired:

```
jwt.decode()

↓

raise ExpiredSignatureError

↓

Python searches except blocks

↓

ExpiredSignatureError matches

↓

Execute corresponding block
```

Execution never reaches the later exception handlers.

---

# Exception Hierarchy

PyJWT exceptions follow an inheritance hierarchy.

```
Exception
    │
    ▼
PyJWTError
    │
    ├── ExpiredSignatureError
    ├── DecodeError
    ├── InvalidSignatureError
    ├── InvalidAlgorithmError
    └── ...
```

Because of inheritance, exception ordering matters.

Correct:

```python
except ExpiredSignatureError:
    ...

except PyJWTError:
    ...
```

Incorrect:

```python
except PyJWTError:
    ...

except ExpiredSignatureError:
    ...
```

The generic exception would capture every JWT-related exception before the specific handler is reached.

---

# Returning Payload Instead of Boolean

Instead of

```python
True
```

the utility returns the decoded payload.

```python
payload = verify_token(token)
```

Advantages:

- avoids decoding JWT multiple times
- immediately provides claims
- supports future authorization logic
- improves reusability

The caller can directly access:

```
merchant_id

role

permissions

exp
```

without another decode operation.

---

# Separation of Concerns

The project separates cryptographic validation from business decisions.

```
verify_token()

↓

Validates JWT
```

```
Logout Service

↓

Determines logout behaviour
```

Examples:

Protected API

```
Expired Token

↓

401 Unauthorized
```

Refresh API

```
Expired Token

↓

401 Unauthorized
```

Logout API

```
Expired Token

↓

verify_exp=False

↓

Continue Logout
```

The utility remains unchanged.

Only the service decides the business behavior.

---

# Repository Responsibilities

The repository only performs persistence operations.

Its responsibility is:

```
Locate Refresh Token

↓

Update revoked_at
```

The repository does not:

- decide HTTP responses
- raise authentication errors
- commit transactions

Transaction ownership remains with the service layer.

---

# Service Responsibilities

The service orchestrates the business workflow.

```
Verify JWT

↓

Hash Token

↓

Ask Repository to Revoke Session

↓

Commit Transaction

↓

Return Success
```

The service is responsible for preserving the API contract.

---

# Lessons Learned

Although Logout is a small API from an implementation perspective, it demonstrates several important software engineering principles.

Key takeaways:

- Small APIs often hide significant architectural complexity.
- Utility functions should have a single responsibility.
- Business rules belong in the service layer rather than utility functions.
- Idempotency should influence implementation decisions.
- Repository classes should remain persistence-focused.
- Understanding exception hierarchies prevents subtle bugs.
- Returning useful objects instead of booleans increases reusability.
- A reusable utility should expose configurable behavior instead of embedding endpoint-specific logic.
- Well-designed APIs are driven by business contracts rather than convenience.