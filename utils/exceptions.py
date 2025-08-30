"""
Custom exceptions for the League Auto Picker application.
"""


class LeagueClientDisconnected(Exception):
    """
    Raised when the League client is no longer accessible.

    This exception indicates that the League client has been closed
    or is otherwise unreachable, and the script should restart.
    """

    pass
