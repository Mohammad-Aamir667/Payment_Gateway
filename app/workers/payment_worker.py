from enum import Enum
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.infrastructure.database import SessionLocal
from app.payment.exceptions import (
    MerchantPaymentMethodNotFoundError,
    PaymentMethodNotFoundError,
    PaymentNotFoundError,
    ProviderCommunicationError,
    UnknownProviderStatusError,
)
from app.payment.service import PaymentService
from app.merchant.models import Merchant  # noqa: F401
from app.payment.models import Payment 

class PaymentJobResult(str, Enum):
    COMPLETED = "COMPLETED"
    RETRY = "RETRY"
    DISCARD = "DISCARD"


def process_payment_job(payment_id: UUID) -> PaymentJobResult:

    db = SessionLocal()

    try:
        payment_service = PaymentService()

        payment_service.process_payment(
            db=db,
            payment_id=payment_id,
        )

        return PaymentJobResult.COMPLETED
 
    except (
        ProviderCommunicationError,
        OperationalError,
    ) as exc:

        print(
            f"Retryable payment processing error "
            f"for {payment_id}: {exc}"
        )

        db.rollback()

        return PaymentJobResult.RETRY

    except (
        PaymentNotFoundError,
        MerchantPaymentMethodNotFoundError,
        PaymentMethodNotFoundError,
        UnknownProviderStatusError,
    ) as exc:

        print(
            f"Non-retryable payment processing error "
            f"for {payment_id}: {exc}"
        )

        db.rollback()

        return PaymentJobResult.DISCARD
    # left the cases of programming errors and unexpected errors to be handled by the caller of this function, which is the RabbitMQ consumer. The consumer will log the error and decide whether to requeue or discard the message based on the type of error.
    except Exception as exc:

        print(
            f"Unexpected error during payment processing "
            f"for {payment_id}: {exc}"
        )

        db.rollback()
        return PaymentJobResult.DISCARD        

        
    finally:
        db.close()