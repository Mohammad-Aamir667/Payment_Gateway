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