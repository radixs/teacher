class SessionNotFoundError(Exception):
    """Raised when neither in-memory nor persisted storage contains a session."""

