from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.payment_methods.models import PaymentMethod


PAYMENT_METHODS = [
    {
        "code": "UPI",
        "display_name": "UPI",
    },
    {
        "code": "CARD",
        "display_name": "Card",
    },
    {
        "code": "NET_BANKING",
        "display_name": "Net Banking",
    },
    {
        "code": "WALLET",
        "display_name": "Wallet",
    },
]


def seed_payment_methods() -> None:
    db: Session = SessionLocal()

    try:
        for method in PAYMENT_METHODS:

            existing_payment_method = (
                db.query(PaymentMethod)
                .filter(
                    PaymentMethod.code == method["code"],
                )
                .first()
            )

            if existing_payment_method:
                continue

            payment_method = PaymentMethod(
                code=method["code"],
                display_name=method["display_name"],
                is_active=True,
            )

            db.add(payment_method)

        db.commit()

        print("Payment methods seeded successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_payment_methods()