from unittest import result
from uuid import UUID
from app.infrastructure.database import SessionLocal
from app.payment.service import PaymentService
from app.merchant.models import Merchant  # noqa: F401
from app.payment.models import Payment 
def process_payment_job(payment_id: UUID) -> None:
    db = SessionLocal()

   
    try:
        payment_service = PaymentService()
        payment= payment_service.process_payment(
            db=db,
            payment_id=payment_id,
        )
        
        print(f"Payment processed successfully: {payment.payment_id}, status: {payment.status}")
    except Exception as e:
        print(f"Error processing payment {payment_id}: {e}")  
      
    finally:
        db.close()