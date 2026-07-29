# Payment Gateway Backend
# Document 03 - Authentication Flow

---

# 1. Purpose of this Document

Authentication is one of the most important parts of our payment gateway.

This document explains:

- How Signup works
- Why Authentication is implemented as a Service
- Responsibilities of each component
- How data flows between components
- Why each architectural decision was made

This document intentionally focuses on **business flow**, not FastAPI syntax.

---

# 2. What is Authentication?

Authentication answers one question:

> "Who is making this request?"

Our payment gateway allows merchants to access protected APIs.

Before a merchant can create payments, issue refunds, or view transactions, we must verify their identity.

Authentication is therefore a **business capability**, not merely a technical feature.

---

# 3. Components Involved

Signup involves multiple components.

```

Client

│

▼

Router

│

▼

AuthService

│

├────────────► MerchantRepository

│

├────────────► RefreshTokenRepository

│

├────────────► Password Utilities

│

└────────────► JWT Utilities

```

Notice something important.

AuthService sits in the middle.

It coordinates everything.

No other component knows the complete signup process.

---

# 4. Why AuthService Exists

This is one of the most important design decisions.

Suppose signup logic lived inside the Router.

```

Router

↓

Check Email

↓

Hash Password

↓

Generate JWT

↓

Save Merchant

↓

Store Refresh Token

↓

Return Response

```

Now imagine:

Tomorrow we build

- GraphQL
- CLI
- Background Worker

All of them need signup.

Would we copy this code everywhere?

No.

Instead,

all authentication logic lives inside one place.

```

Router

↓

AuthService.signup()

```

The Router simply delegates work.

---

# 5. Responsibility of AuthService

AuthService owns authentication.

Its responsibilities include:

- Register merchant
- Login merchant
- Verify password
- Generate Access Token
- Generate Refresh Token
- Store Refresh Token
- Logout
- Refresh Session

Notice

AuthService does NOT know SQL.

It asks repositories to persist data.

---

# 6. MerchantRepository Responsibility

MerchantRepository only knows how to work with Merchant data.

Examples:

```python
create()

get_by_email()

get_by_id()

update()
```

It should never:

- Hash passwords
- Generate JWT
- Verify credentials

Those are business decisions.

MerchantRepository only performs persistence.

---

# 7. RefreshTokenRepository Responsibility

RefreshTokenRepository owns refresh token persistence.

Responsibilities

- Save refresh token
- Find refresh token
- Revoke refresh token
- Delete expired tokens

Notice

It knows nothing about JWT generation.

It simply stores token metadata.

---

# 8. Password Utility

Password hashing is not a business capability.

It is a reusable utility.

Responsibilities

```python
hash_password()

verify_password()
```

Nothing more.

This is why it is implemented as simple functions rather than a class.

---

# 9. JWT Utility

JWT generation is also reusable.

Responsibilities

```python
create_access_token()

create_refresh_token()

decode_token()
```

Again,

this is not business logic.

It is reusable infrastructure.

---

# 10. Signup Flow

The complete signup flow looks like this.

```

Client

│

▼

POST /auth/signup

│

▼

Router

│

▼

AuthService.signup()

│

├── Check if email exists

│

├── Hash password

│

├── Create Merchant

│

├── MerchantRepository.create()

│

├── Generate Access Token

│

├── Generate Refresh Token

│

├── Hash Refresh Token

│

├── RefreshTokenRepository.create()

│

└── Return Merchant + Tokens

│

▼

Router

│

├── Attach Refresh Cookie

│

└── Return SignupResponse

│

▼

Client

```

Notice

The Router never creates JWT.

Repository never hashes password.

JWT utility never talks to database.

Every component performs only one responsibility.

---

# 11. Why Does AuthService Use MerchantRepository?

AuthService needs merchant data.

But it should not know

- SQL
- PostgreSQL
- SQLAlchemy

Instead

it asks

```python
merchant_repository.get_by_email(...)
```

The repository decides how to retrieve it.

This separation allows us to change database technology without changing business logic.

---

# 12. Why Store Refresh Tokens?

Access Tokens are short-lived.

Refresh Tokens live much longer.

Suppose a refresh token is stolen.

If we never stored it,

we could never revoke it.

Instead,

we store only

```

SHA-256 Hash

```

inside the database.

Now we can

- revoke sessions
- logout devices
- detect token reuse
- expire sessions

without storing the actual refresh token.

---

# 13. Why Hash Refresh Tokens?

Suppose someone steals the database.

If refresh tokens were stored directly,

the attacker immediately owns every merchant session.

Instead

we store

```

hash(refresh_token)

```

Now

even database theft does not reveal usable refresh tokens.

---

# 14. Why Return Access Token but not Refresh Token?

Access Token

↓

Short-lived

↓

Frontend needs it

↓

Returned in JSON

---

Refresh Token

↓

Long-lived

↓

Stored inside HttpOnly Cookie

↓

JavaScript cannot read it

This significantly reduces the damage of XSS attacks.

---

# 15. Why Doesn't Repository Generate Tokens?

Imagine

MerchantRepository generated JWT.

Now Repository would know

- SQL
- JWT
- Authentication

Its responsibilities become mixed.

Repository exists only for persistence.

Business decisions belong to AuthService.

---

# 16. Transaction Boundary

Signup performs multiple operations.

- Insert Merchant
- Insert Refresh Token

These operations should succeed together.

If merchant is created

but refresh token insertion fails,

the transaction should rollback.

This preserves database consistency.

AuthService coordinates this transaction.

Repositories simply execute persistence operations.

---

# 17. Returning From AuthService

Our service returns

```python
merchant,
access_token,
refresh_token
```

Notice

It does NOT return HTTP responses.

It does NOT return JSON.

Those belong to the Router.

AuthService returns business objects.

Router converts them into HTTP responses.

This separation makes AuthService reusable outside FastAPI.

---

# 18. Router Responsibility After Service Returns

After

```python
merchant,
access_token,
refresh_token
```

are returned,

Router performs HTTP responsibilities.

It

- converts Merchant ORM to Pydantic Response
- attaches HttpOnly Cookie
- returns SignupResponse

Notice

Everything here is HTTP-related.

Business work has already finished.

---

# 19. Why This Design Scales

Suppose tomorrow we add

Google Login.

Only AuthService changes.

Repositories barely change.

Router barely changes.

Suppose tomorrow JWT becomes PASETO.

Only JWT utility changes.

AuthService hardly changes.

Good architecture isolates change.

That is the biggest goal of layered design.

---

# Key Takeaways

✔ Authentication is a business capability.

✔ AuthService owns authentication.

✔ Repository owns persistence.

✔ Utilities provide reusable infrastructure.

✔ Router owns HTTP.

✔ Password hashing belongs to utilities.

✔ JWT generation belongs to utilities.

✔ Refresh Tokens are stored as hashes.

✔ Service returns business objects.

✔ Router returns HTTP responses.

---

# Interview Notes

### Why create AuthService?

To centralize authentication business logic.

---

### Why doesn't Repository generate JWT?

Because persistence and authentication are separate responsibilities.

---

### Why hash Refresh Tokens?

To protect sessions if the database is compromised.

---

### Why return Access Token in JSON?

Because the frontend needs it for Authorization headers.

---

### Why store Refresh Token in HttpOnly Cookie?

To prevent JavaScript from accessing long-lived credentials.

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

Return

```
merchant,
access_token,
refresh_token
```

↓

Router

↓

Set Refresh Cookie

↓

Return

```python
SignupResponse(
    merchant=...,
    access_token=...
)
```