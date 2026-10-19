"""Translate low-level PyMongo errors into meaningful domain errors."""
from contextlib import contextmanager

from pymongo.errors import DuplicateKeyError, WriteError

from services.errors import DatabaseValidationError, DuplicateError

DOCUMENT_VALIDATION_FAILURE = 121  # MongoDB error code for $jsonSchema rejection


@contextmanager
def translate_write_errors(duplicate_message: str):
    try:
        yield
    except DuplicateKeyError as exc:
        raise DuplicateError(duplicate_message) from exc
    except WriteError as exc:
        if exc.code == DOCUMENT_VALIDATION_FAILURE:
            raise DatabaseValidationError(
                f"MongoDB rejected the document: it violates the collection's JSON Schema validator. "
                f"({exc.details.get('errmsg', exc)})") from exc
        raise  # anything else is unexpected: never hide it
