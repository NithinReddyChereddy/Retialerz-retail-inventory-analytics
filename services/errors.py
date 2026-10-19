"""Domain exceptions with meaningful messages (never swallowed silently)."""


class AppError(Exception):
    """Base class for all expected business-rule failures."""


class InputValidationError(AppError):
    """User input failed Python-side validation."""


class DuplicateError(AppError):
    """A unique identifier (sku / supplier_id / movement_id) already exists."""


class NotFoundError(AppError):
    """A referenced product or supplier does not exist."""


class InsufficientStockError(AppError):
    """The operation would make stock negative."""


class DeletionBlockedError(AppError):
    """Deletion refused to protect history / referential integrity."""


class DatabaseValidationError(AppError):
    """MongoDB's own $jsonSchema validator rejected the document."""


class StockConsistencyError(AppError):
    """Stock update and movement record could not be kept consistent (needs attention)."""
