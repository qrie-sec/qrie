"""
Custom exceptions for API error handling.

These exceptions allow specific HTTP status codes to be returned
while maintaining fail-fast principles and letting exceptions bubble up.
"""


class ApiException(Exception):
    """Base exception for API errors with specific HTTP status codes"""
    status_code = 500
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(ApiException):
    """Raised when request validation fails (400 Bad Request)"""
    status_code = 400


class NotFoundError(ApiException):
    """Raised when a requested resource is not found (404 Not Found)"""
    status_code = 404


class ConflictError(ApiException):
    """Raised when a request conflicts with current state (409 Conflict)"""
    status_code = 409
