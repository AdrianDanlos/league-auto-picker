"""
Decorators for handling common patterns in the League Auto Picker.
"""

import functools
import requests
from .exceptions import LeagueClientDisconnected


def handle_connection_errors(func):
    """
    Decorator that handles connection errors gracefully by converting them
    to LeagueClientDisconnected exceptions.

    This reduces boilerplate code throughout the application by automatically
    catching connection-related errors and raising the appropriate exception
    that the main application loop knows how to handle.

    Usage:
        @handle_connection_errors
        def some_api_call():
            response = requests.get(url, auth=auth, verify=False)
            return response
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException,
            RuntimeError,
        ):
            # League client has disconnected - raise a generic exception
            raise LeagueClientDisconnected()

    return wrapper
