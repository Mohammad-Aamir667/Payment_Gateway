class PSPTimeoutError(Exception):
    """The simulated PSP did not respond within the expected time."""


class ResponseLostError(Exception):
    """The simulated PSP processed the payment, but the response was lost."""


class PSPInternalError(Exception):
    """Simulated internal error in the PSP."""    