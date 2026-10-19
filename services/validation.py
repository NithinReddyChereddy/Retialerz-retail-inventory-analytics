"""Python-side input validation helpers (business rules MongoDB schema cannot express)."""
import math
import re
from typing import Any, Optional

from services.errors import InputValidationError

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[0-9(][0-9\s\-().]{5,19}$")


def clean_text(value: Any, field: str, required: bool = True, max_len: int = 120) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise InputValidationError(f"{field} must be text.")
    value = value.strip()
    if required and not value:
        raise InputValidationError(f"{field} is required and cannot be blank.")
    if len(value) > max_len:
        raise InputValidationError(f"{field} must be at most {max_len} characters.")
    return value


def clean_identifier(value: Any, field: str) -> str:
    value = clean_text(value, field, max_len=40)
    if re.search(r"\s", value):
        raise InputValidationError(f"{field} must not contain spaces.")
    return value.upper()


def clean_price(value: Any, field: str = "Unit price") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputValidationError(f"{field} must be a number.")
    if math.isnan(value) or math.isinf(value):
        raise InputValidationError(f"{field} must be a finite number.")
    if value < 0:
        raise InputValidationError(f"{field} cannot be negative.")
    return round(float(value), 2)


def clean_int(value: Any, field: str, minimum: Optional[int] = 0) -> int:
    if isinstance(value, bool):
        raise InputValidationError(f"{field} must be a whole number.")
    if isinstance(value, float):
        if not value.is_integer():
            raise InputValidationError(f"{field} must be a whole number.")
        value = int(value)
    if not isinstance(value, int):
        raise InputValidationError(f"{field} must be a whole number.")
    if minimum is not None and value < minimum:
        raise InputValidationError(f"{field} must be at least {minimum}.")
    return value


def clean_email(value: Any, required: bool = False) -> str:
    value = clean_text(value, "Email", required=required)
    if value and not _EMAIL_RE.match(value):
        raise InputValidationError(f"'{value}' is not a valid email address.")
    return value


def clean_phone(value: Any, required: bool = False) -> str:
    value = clean_text(value, "Phone", required=required, max_len=25)
    if value:
        digits = re.sub(r"\D", "", value)
        if not _PHONE_RE.match(value) or not 7 <= len(digits) <= 15:
            raise InputValidationError(
                f"'{value}' is not a valid phone number (7-15 digits; + - ( ) . and spaces allowed).")
    return value
