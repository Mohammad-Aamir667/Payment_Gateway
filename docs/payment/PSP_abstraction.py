# Payment Service Provider Abstraction

## Purpose

The payment gateway should not make its core payment service dependent on a specific Payment Service Provider (PSP).

The gateway may initially use a simulated PSP for testing, but later it may integrate with providers such as Stripe, Juspay, Razorpay, or another external provider.

The gateway therefore defines its own internal contract for what a payment provider must be able to do.

---

# 1. The Basic Problem

Without an abstraction, the payment service could directly depend on a concrete provider:

```python
class PaymentService:

    def process_payment(self, ...):
        provider = SimulatedPaymentServiceProvider()

        result = provider.initiate_payment(
            ...
        )
```

This creates a direct dependency:

```text
PaymentService
      ↓
SimulatedPaymentServiceProvider
```

If the gateway later moves to Stripe:

```text
PaymentService
      ↓
StripePaymentServiceProvider
```

the payment service itself has to change.

If different payment methods use different providers, the service can eventually become filled with provider-specific logic:

```python
if payment_method == "CARD":
    # Stripe

elif payment_method == "UPI":
    # Juspay

elif payment_method == "WALLET":
    # another provider
```

This mixes two different responsibilities:

* Payment business logic
* PSP selection and provider-specific implementation

---

# 2. PaymentServiceProvider

The gateway therefore defines a common abstraction:

```python
from abc import ABC, abstractmethod


class PaymentServiceProvider(ABC):

    @abstractmethod
    def initiate_payment(
        self,
        payment_id,
        amount,
        currency,
        payment_method,
        payment_metadata,
    ):
        pass
```

This class does not actually process a payment.

It defines what the gateway expects from a payment provider.

---

# 3. What Is ABC?

`ABC` means **Abstract Base Class**.

```python
from abc import ABC

class PaymentServiceProvider(ABC):
    ...
```

By inheriting from `ABC`, the class can define abstract methods that subclasses are required to implement.

Think of `ABC` as saying:

> This class is intended to define a contract for other classes rather than being a concrete payment provider itself.

`PaymentServiceProvider` is therefore not the simulated PSP.

It is the definition of what a PSP must provide to the gateway.

---

# 4. What Is @abstractmethod?

`@abstractmethod` marks a method as required.

```python
from abc import ABC, abstractmethod


class PaymentServiceProvider(ABC):

    @abstractmethod
    def initiate_payment(
        self,
        payment_id,
        amount,
        currency,
        payment_method,
        payment_metadata,
    ):
        pass
```

This means:

> Any concrete class that inherits from `PaymentServiceProvider` must implement `initiate_payment()` before it can be instantiated.

For example:

```python
class SimulatedPaymentServiceProvider(
    PaymentServiceProvider
):
    pass
```

This class has not implemented `initiate_payment()`.

Therefore Python will not allow:

```python
provider = SimulatedPaymentServiceProvider()
```

because the abstract method is still unimplemented.

---

# 5. Concrete PSP Implementations

A simulated provider can now implement the contract:

```python
class SimulatedPaymentServiceProvider(
    PaymentServiceProvider
):

    def initiate_payment(
        self,
        payment_id,
        amount,
        currency,
        payment_method,
        payment_metadata,
    ):
        # Simulation logic
        ...
```

Later:

```python
class StripePaymentServiceProvider(
    PaymentServiceProvider
):

    def initiate_payment(
        self,
        payment_id,
        amount,
        currency,
        payment_method,
        payment_metadata,
    ):
        # Stripe-specific integration
        ...
```

And:

```python
class JuspayPaymentServiceProvider(
    PaymentServiceProvider
):

    def initiate_payment(
        self,
        payment_id,
        amount,
        currency,
        payment_method,
        payment_metadata,
    ):
        # Juspay-specific integration
        ...
```

The three classes can have completely different internal implementations.

The important part is that the gateway sees the same operation:

```python
provider.initiate_payment(...)
```

---

# 6. Why Is This Called a Contract?

The word **contract** means that the gateway establishes a rule:

> A class that acts as a Payment Service Provider for this gateway must provide `initiate_payment()` with the gateway-defined interface.

The parent class defines the expected capability.

The child class provides the implementation.

Therefore:

```text
PaymentServiceProvider
        │
        │ defines contract
        ▼
initiate_payment()
        │
        ├── Simulated PSP implementation
        ├── Stripe PSP implementation
        └── Juspay PSP implementation
```

The parent does not tell every provider *how* to process the payment.

It only tells them *what capability the gateway expects them to expose*.

---

# 7. Why Does the PaymentService Not Need to Know the Provider Type?

This is where polymorphism becomes useful.

Suppose a provider factory returns a provider:

```python
provider = provider_factory.get_provider(payment_method)
```

At runtime, the returned object might be:

```text
StripePaymentServiceProvider
```

or:

```text
JuspayPaymentServiceProvider
```

or:

```text
SimulatedPaymentServiceProvider
```

The `PaymentService` doesn't need to write:

```python
if provider is StripePaymentServiceProvider:
    ...

elif provider is JuspayPaymentServiceProvider:
    ...
```

It simply does:

```python
result = provider.initiate_payment(
    payment_id=payment_id,
    amount=amount,
    currency=currency,
    payment_method=payment_method,
    payment_metadata=payment_metadata,
)
```

Python dispatches the call to the implementation belonging to the actual object returned at runtime.

---

# 8. Runtime Polymorphism

This is a practical example of **runtime polymorphism**.

Suppose:

```python
provider = provider_factory.get_provider(payment_method)
```

At compile time, the exact concrete provider may not be known.

At runtime:

```text
payment_method = CARD
        ↓
provider_factory
        ↓
StripePaymentServiceProvider instance
```

Then:

```python
provider.initiate_payment(...)
```

executes:

```python
StripePaymentServiceProvider.initiate_payment(...)
```

For another payment:

```text
payment_method = UPI
        ↓
provider_factory
        ↓
JuspayPaymentServiceProvider instance
```

The exact same service code:

```python
provider.initiate_payment(...)
```

now executes:

```python
JuspayPaymentServiceProvider.initiate_payment(...)
```

The caller does not need to know which concrete implementation it received.

---

# 9. Why This Is Useful for a Payment Gateway

Different PSPs can have completely different external APIs.

For example, internally the providers might work like:

```text
Stripe
→ Stripe-specific API request

Juspay
→ Juspay-specific API request

Simulator
→ deterministic fake result
```

Their external APIs may use different:

* request formats
* authentication mechanisms
* endpoint names
* response formats
* error formats

The gateway hides those differences inside the concrete provider implementations.

The PaymentService deals only with the gateway's common abstraction:

```text
PaymentService
       ↓
PaymentServiceProvider
       ↓
Concrete PSP
```

This keeps provider-specific integration details out of the payment business logic.

---

# 10. What the PaymentService Is Responsible For

The PaymentService should handle gateway-level payment logic such as:

```text
Create Payment
Validate Payment
Maintain Payment State
Create Payment History
Manage Payment Transaction
```

It should not need to know:

```text
Is this Stripe?
Is this Juspay?
Which Stripe URL should I call?
How does Juspay authenticate?
How does Stripe format its request?
```

Those concerns belong inside the provider.

---

# 11. Complete Relationship

The final structure looks like:

```text
                     PaymentServiceProvider
                              │
                     abstract contract
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
      Simulated PSP        Stripe PSP       Juspay PSP
             │                │                │
             └────────────────┼────────────────┘
                              │
                       initiate_payment()
                              ▲
                              │
                       PaymentService
```

The PaymentService only depends on the common contract.

---

# 12. Important Python Limitation

`ABC` and `@abstractmethod` enforce that the method exists, but Python does not provide the same compile-time signature enforcement found in languages such as Java or C#.

For example, a subclass could technically write:

```python
class BadProvider(PaymentServiceProvider):

    def initiate_payment(self, payment_id):
        ...
```

Python will allow the class definition.

The problem appears when the service calls it with the full expected arguments.

Type hints and static type checkers such as mypy or Pyright can provide stronger checking.

Therefore the abstraction provides:

1. A documented common interface.
2. Runtime enforcement that the abstract method is implemented.
3. Polymorphic behavior.
4. A clean boundary between payment business logic and PSP-specific implementation.

---

# Core Principle

The important idea is not merely:

> "Every PSP must have a method called `initiate_payment`."

The deeper principle is:

> **The PaymentService depends on a capability, not on a concrete provider.**

The gateway defines what a provider must expose, while each provider decides how to implement that capability.

That is why `PaymentServiceProvider` exists even though every individual PSP could simply define `initiate_payment()` on its own.
