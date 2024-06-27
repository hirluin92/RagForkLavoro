
import requests
from tenacity import retry_if_exception
from tenacity.wait import wait_base

class retry_if_http_error(retry_if_exception):
    """Retry strategy that retries if the exception is an ``HTTPError`` with
    a 429 status code.

    """

    def __init__(self):
        def is_http_429_500_error(exception):
            if isinstance(exception,
                           requests.exceptions.HTTPError):
                return (
                    exception.response.status_code == 429 
                 or exception.response.status_code == 500)

            return (
                isinstance(exception,
                           requests.exceptions.ConnectionError) or
                isinstance(exception,
                           requests.exceptions.Timeout)
            )

        super().__init__(predicate=is_http_429_500_error)

class wait_for_retry_after_header(wait_base):
    """Wait strategy that tries to wait for the length specified by
    the Retry-After header, or the underlying wait strategy if not.
    See RFC 6585 § 4.

    Otherwise, wait according to the fallback strategy.
    """
    def __init__(self, fallback):
        self.fallback = fallback

    def __call__(self, retry_state):
        # retry_state is an instance of tenacity.RetryCallState.  The .outcome
        # property is the result/exception that came from the underlying function.
        exception = retry_state.outcome.exception()
        if isinstance(exception,
                      requests.exceptions.HTTPError) and exception.request:
            retry_after = exception.request.headers.get("Retry-After", 1)
            try:
                return int(retry_after)
            except (TypeError, ValueError):
                pass

        return self.fallback(retry_state)