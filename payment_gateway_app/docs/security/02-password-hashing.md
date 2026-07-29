# Payment Gateway Backend
# Security - 02 Password Hashing

---

# 1. Purpose of this Document

Passwords should never be stored in plain text.

That is a well-known rule.

However, while implementing our Signup API, we made several important design decisions beyond simply "using bcrypt."

This document explains:

- Why we chose bcrypt.
- Why we didn't use SHA-256.
- Why passwords are encoded before hashing.
- Why bcrypt returns bytes.
- Why we decode before storing.
- Why password verification does not decrypt anything.
- Why refresh tokens are hashed differently.

This document focuses on **our project's implementation**, not cryptography theory.

---

# 2. Our Password Flow

Whenever a merchant signs up,

the password follows this lifecycle.

```
Plain Password

↓

UTF-8 Encoding

↓

bcrypt

↓

Hashed Password

↓

Database
```

Later,

during Login,

```
Plain Password

↓

UTF-8 Encoding

↓

bcrypt.checkpw()

↓

True / False
```

Notice

At no point is the password decrypted.

---

# 3. Why We Hash Passwords

Suppose our Merchant table looked like this.

| Email | Password |
|--------|----------|
| john@example.com | Password123 |

If the database is compromised,

every password becomes visible immediately.

Instead,

we store

```
$2b$12$...
```

instead of

```
Password123
```

Even database administrators cannot recover the original password.

---

# 4. Why We Chose bcrypt

One of the first questions we discussed was

> Why not SHA-256?

Because passwords are fundamentally different from refresh tokens.

Passwords are chosen by humans.

```
password123

admin123

qwerty

welcome
```

Attackers already know these common passwords.

If hashing is fast,

millions of guesses can be made every second.

bcrypt intentionally makes hashing slow.

That makes brute-force attacks significantly more expensive.

For passwords,

slow hashing is a security feature.

---

# 5. Why We Didn't Use SHA-256

SHA-256 is an excellent cryptographic hash function.

However,

it is designed to be fast.

Fast hashing is useful for

- file verification
- digital signatures
- token lookup

It is not ideal for human passwords.

A fast hash allows attackers to test billions of password guesses quickly.

Therefore,

we reserve SHA-256 for Refresh Tokens,

not passwords.

---

# 6. Why We Encode the Password

One question we discussed during implementation was

> Why do we call `encode()`?

Python strings look like this.

```python
password = "MyPassword123"
```

Internally,

bcrypt works only with bytes.

Therefore,

we convert

```
Python String

↓

UTF-8 Encoding

↓

Bytes
```

Example

```python
password.encode("utf-8")
```

Without encoding,

bcrypt cannot process the password.

---

# 7. Why bcrypt Returns Bytes

bcrypt also returns bytes.

```python
hashed_password = bcrypt.hashpw(...)
```

Result

```python
b"$2b$12$..."
```

The leading

```
b
```

indicates a byte sequence.

Databases typically store text,

not Python byte objects.

Therefore,

we convert it back.

```
Bytes

↓

decode("utf-8")

↓

String

↓

Database
```

---

# 8. Why We Decode Before Storing

During Signup,

our helper function returns

```python
hash.decode("utf-8")
```

This is not changing the hash.

It is simply converting

```
Bytes

↓

String
```

so SQLAlchemy can store it cleanly inside a TEXT or VARCHAR column.

---

# 9. Why verify_password() Doesn't Decrypt Anything

Another question we discussed.

Many beginners think

```
Stored Hash

↓

Decrypt

↓

Compare
```

That never happens.

Instead,

bcrypt hashes the newly entered password again,

using information embedded inside the stored hash.

```
Entered Password

↓

bcrypt.checkpw()

↓

Compare Hashes

↓

True / False
```

The original password is never recovered.

---

# 10. Why bcrypt Can Verify Without Decrypting

The stored bcrypt hash contains everything needed for verification.

It includes

- algorithm version
- work factor (cost)
- salt
- hash

When `checkpw()` runs,

bcrypt extracts these values,

rehashes the entered password,

and compares the result.

If both hashes match,

the password is correct.

No decryption is involved.

---

# 11. bcrypt's 72-Byte Limitation

While implementing Refresh Tokens,

we discovered an important limitation.

bcrypt only considers the first **72 bytes** of input.

Passwords rarely exceed this length,

so this is usually not a problem.

Refresh Tokens, however,

are long, randomly generated strings.

Using bcrypt would ignore everything beyond 72 bytes.

That makes bcrypt unsuitable for hashing refresh tokens.

This discovery led us to redesign our Refresh Token storage.

---

# 12. Why Passwords and Refresh Tokens Use Different Hash Functions

Although both are called "hashing,"

they solve different problems.

Passwords

```
Human Generated

↓

Predictable

↓

Need Slow Hashing

↓

bcrypt
```

Refresh Tokens

```
Randomly Generated

↓

High Entropy

↓

Need Fast Lookup

↓

SHA-256
```

The choice of algorithm depends on the nature of the data,

not on whether something is called a password or token.

---

# 13. Our Password Utility

The Password Utility has only two responsibilities.

```
hash_password()

↓

Generate bcrypt hash
```

and

```
verify_password()

↓

Compare entered password
```

It knows nothing about

- Merchant
- JWT
- Refresh Tokens
- Database
- HTTP

This keeps the utility reusable and focused.

---

# 14. Password Lifecycle in Our Project

```
Merchant Signup

↓

Receive Plain Password

↓

UTF-8 Encoding

↓

bcrypt.hashpw()

↓

decode("utf-8")

↓

Store Hash

↓

Merchant Login

↓

Receive Password

↓

UTF-8 Encoding

↓

bcrypt.checkpw()

↓

Authentication Success / Failure
```

---

# Why We Didn't Choose Other Designs

## Why not store plain passwords?

Because a database compromise would expose every user's credentials.

---

## Why not use SHA-256?

Because passwords are predictable and require slow hashing to resist brute-force attacks.

---

## Why not decrypt stored passwords?

Because passwords are never encrypted.

They are hashed.

Hashing is intentionally one-way.

---

## Why not use bcrypt for Refresh Tokens?

Because Refresh Tokens are already random and bcrypt ignores input beyond 72 bytes.

SHA-256 is a better fit for secure lookup.

---

# Key Takeaways

✔ Passwords are hashed before storage.

✔ bcrypt is intentionally slow.

✔ Passwords are encoded into bytes before hashing.

✔ bcrypt returns bytes, which we decode before storing.

✔ Password verification never decrypts anything.

✔ bcrypt internally performs a secure comparison using the stored hash.

✔ Passwords and Refresh Tokens require different hashing strategies because they solve different security problems.

---

# Interview Notes

★★★★★ Why use bcrypt instead of SHA-256 for passwords?

Passwords are human-generated and predictable. bcrypt is intentionally slow, making brute-force attacks significantly more expensive.

---

★★★★★ Why do we call `encode("utf-8")` before hashing?

bcrypt accepts bytes, not Python strings.

---

★★★★★ Why do we call `decode("utf-8")` before storing?

bcrypt returns bytes. Decoding converts them into a string suitable for database storage.

---

★★★★☆ Does `verify_password()` decrypt the password?

No. It hashes the entered password again using parameters stored in the bcrypt hash and compares the result.

---

★★★★☆ Why doesn't bcrypt work well for Refresh Tokens?

bcrypt only considers the first 72 bytes of input. Refresh Tokens are long random values, so SHA-256 is a better choice.

---

# Connection With Our Project

```
POST /auth/signup

↓

Receive Password

↓

PasswordUtility.hash_password()

↓

UTF-8 Encoding

↓

bcrypt.hashpw()

↓

decode("utf-8")

↓

MerchantRepository.create()

↓

Store Merchant
```

Later,

```
POST /auth/login

↓

Receive Password

↓

PasswordUtility.verify_password()

↓

bcrypt.checkpw()

↓

Authentication Result

↓

Generate Tokens
```

The Password Utility is responsible only for hashing and verification.

It has no knowledge of authentication, JWTs, HTTP, or the database, which keeps its responsibility focused and aligned with our architecture.