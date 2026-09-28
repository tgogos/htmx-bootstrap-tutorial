"""Custom auth exceptions."""


class LoginRequired(Exception):
    """Raised when an HTML route requires a logged-in user."""
    pass
