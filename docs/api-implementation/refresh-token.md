# Refresh Token API Implementation

## Overview

The Refresh Token API is responsible for issuing a new Access Token and rotating the existing Refresh Token without requiring the merchant to log in again.

Unlike the Signup or Logout APIs, this endpoint does not introduce new architectural components. Instead, it demonstrates how previously implemented utilities and repositories are orchestrated together to securely renew an authenticated session.

Most authentication concepts such as JWT structure, Refresh Tokens, Token Hashing and Authentication Flow are documented separately in:

- security/03-jwt.md
- security/04-refresh-token.md
- security/05-token-hashing.md
- architecture/03-authentication-overview.md

This document focuses only on implementation decisions.

---

# High Level Flow

```
Client

↓

Read Refresh Token Cookie

↓

Verify JWT Signature

↓

Hash Refresh Token

↓

Find Session

↓

Validate Session

↓

Validate Merchant

↓

Generate New Tokens

↓

Revoke Old Session

↓

Create New Session

↓

Commit Transaction

↓

Return Access Token + Set Cookie
```

---

# Reusing Existing Utilities

One design goal of this endpoint was to avoid creating API-specific utility functions.

Instead of creating separate methods such as

- verify_refresh_token()
- verify_logout_token()

the project uses a single reusable utility:

```python
verify_token(token, verify_exp=True)
```

The utility supports different authentication scenarios through configuration instead of code duplication.

For the Refresh API, expiration validation remains enabled because an expired Refresh Token should not generate new credentials.

```python
payload = verify_token(token)
```

The same utility is reused by protected APIs and keeps authentication logic centralized.

---

# Session Lookup

After JWT verification succeeds, the Refresh Token itself is not trusted as the session source.

Instead, the token is hashed and the database becomes the source of truth.

```
Refresh Token

↓

SHA-256 Hash

↓

Database Lookup

↓

RefreshToken Session
```

This approach prevents storing raw Refresh Tokens in the database while still allowing session lookup.

---

# Business Validation

JWT verification only proves that the token is authentic.

Before issuing new credentials, additional business validations are performed.

The implementation validates:

- Refresh Token session exists.
- Session has not been revoked.
- Session has not expired.
- Merchant still exists.
- Merchant account is ACTIVE.

Each validation answers a different business question.

| Validation | Purpose |
|------------|---------|
| JWT Verification | Can the token be trusted? |
| Session Exists | Is there an active login session? |
| Revoked | Has this session already been terminated? |
| Expired | Is the session still within its lifetime? |
| Merchant Exists | Does the account still exist? |
| Merchant Active | Is the account still allowed to authenticate? |

Only when all validations succeed are new credentials generated.

---

# Merchant Validation

The Refresh Token contains the merchant_id inside its JWT payload.

Although this value is cryptographically trusted after signature verification, the implementation still loads the Merchant from the database.

This is a business validation rather than a security validation.

Possible scenarios include:

- Merchant deleted by an administrator.
- Merchant account marked inactive.
- Merchant disabled after login.

In such cases, the system must not issue new authentication credentials.

---

# Refresh Token Rotation

Instead of extending the lifetime of the existing Refresh Token, the implementation rotates it.

```
RT1

↓

Refresh

↓

RT1 Revoked

↓

RT2 Created
```

This ensures every successful refresh generates a brand-new session token.

The previous session record is retained for auditing purposes by setting `revoked_at`.

---

# Transaction Boundary

Refreshing a session modifies multiple database records.

The implementation performs all database changes inside a single transaction.

```
Revoke Old Session

↓

Create New Session

↓

Commit
```

If any operation fails before commit, SQLAlchemy rolls back the transaction automatically.

This guarantees that the system never reaches an inconsistent state where:

- the old token is revoked but the new one does not exist, or
- a new token exists while the previous session remains active.

---

# Response Design

The endpoint returns authentication data through two separate mechanisms.

## Response Body

```
{
    "access_token": "<jwt>"
}
```

The Access Token is returned inside the response body because frontend applications must read it immediately.

## HttpOnly Cookie

```
Set-Cookie:
refresh_token=...
```

The Refresh Token is stored inside an HttpOnly cookie to prevent JavaScript access and reduce the impact of XSS attacks.

---

# Testing Scenarios

The following scenarios were used to validate the implementation.

| Scenario | Expected Result |
|-----------|-----------------|
| Valid Refresh Token | 200 OK |
| Missing Cookie | 400 Bad Request |
| Invalid JWT | 400 Bad Request |
| Expired Refresh Token | 401 Unauthorized |
| Revoked Session | 401 Unauthorized |
| Session Not Found | 401 Unauthorized |
| Merchant Deleted | 404 Not Found |
| Merchant Inactive | 401 Unauthorized |

After a successful refresh, verify that:

- A new Access Token is returned.
- A new Refresh Token cookie is issued.
- The previous session has `revoked_at` populated.
- A new RefreshToken row exists.
- Other device sessions remain unaffected.

---

# Key Takeaways

This endpoint demonstrates an important design principle followed throughout the project.

Rather than introducing API-specific implementations, the Refresh API composes existing components:

- JWT Utility
- Token Hashing Utility
- Repository Layer
- Service Layer
- SQLAlchemy Transaction Management

The endpoint therefore acts as an orchestration layer that coordinates previously implemented building blocks instead of introducing new infrastructure.