from app.payment.providers.simulated import SimulatedPaymentServiceProvider
from app.payment.provider import PaymentServiceProvider
class PaymentProviderFactory:

    @staticmethod
    def get_provider(payment_method: str) -> PaymentServiceProvider:
        if payment_method == "UPI":
            return SimulatedPaymentServiceProvider()

        if payment_method == "CARD":
            return SimulatedPaymentServiceProvider()

        raise ValueError(
            f"Unsupported payment method: {payment_method}"
        )