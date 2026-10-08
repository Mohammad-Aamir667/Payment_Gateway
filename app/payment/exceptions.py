class ProviderCommunicationError(Exception):
    """Base class for provider communication failures."""


class ProviderTimeoutError(ProviderCommunicationError):
    """Provider request timed out."""


class ProviderInternalError(ProviderCommunicationError):
    """Provider returned an internal/server error."""


class ProviderConnectionError(ProviderCommunicationError):
    """Gateway could not establish/maintain communication with provider."""
class ProviderResponseLostError(ProviderCommunicationError):
    """Provider response was lost after the provider may have processed the request."""    



class PaymentProcessingError(Exception):
    """Base exception for payment processing errors."""


class NonRetryablePaymentProcessingError(PaymentProcessingError):
    """The job should not be retried."""


class PaymentNotFoundError(NonRetryablePaymentProcessingError):
    """The payment referenced by the job does not exist."""


class MerchantPaymentMethodNotFoundError(
    NonRetryablePaymentProcessingError
):
    """The merchant payment method does not exist."""


class PaymentMethodNotFoundError(
    NonRetryablePaymentProcessingError
):
    """The gateway payment method does not exist."""


class UnknownProviderStatusError(
    NonRetryablePaymentProcessingError
):
    """The provider returned a status the gateway does not understand."""    