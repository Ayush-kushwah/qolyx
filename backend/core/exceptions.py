from typing import Optional, Any, Dict

class QolyxException(Exception):
    """Base exception class for all Qolyx system errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.message}"


class EntityNotFoundException(QolyxException):
    """Exception thrown when a requested database entity or resource cannot be located."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details)


class ValidationException(QolyxException):
    """Exception raised when input payload parameters or data schemas breach validation constraints."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details)


class PipelineBlockedException(QolyxException):
    """Exception triggered when a critical data quality failure blocks pipeline progression."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details)


class TrustScoreException(QolyxException):
    """Exception raised when trust scoring arithmetic fails or receives invalid input bounds."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details)
