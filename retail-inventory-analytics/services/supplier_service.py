"""Supplier CRUD with Python-side business rules."""
import re
from typing import Optional

from pymongo.database import Database

import config
from services import validation as v
from services._mongo import translate_write_errors
from services.errors import DeletionBlockedError, NotFoundError

_EDITABLE = ("name", "contact_person", "phone", "email", "city")


def _col(db: Database):
    return db[config.COLLECTION_SUPPLIERS]


def create_supplier(db: Database, supplier_id: str, name: str, contact_person: str = "",
                    phone: str = "", email: str = "", city: str = "") -> dict:
    doc = {
        "supplier_id": v.clean_identifier(supplier_id, "Supplier ID"),
        "name": v.clean_text(name, "Supplier name"),
        "contact_person": v.clean_text(contact_person, "Contact person", required=False),
        "phone": v.clean_phone(phone),
        "email": v.clean_email(email),
        "city": v.clean_text(city, "City", required=False),
    }
    # Unique index on supplier_id enforces "no duplicates" even under concurrency.
    with translate_write_errors(f"Supplier ID '{doc['supplier_id']}' already exists."):
        _col(db).insert_one(doc)  # insert_one adds _id to doc
    return doc


def get_supplier(db: Database, supplier_id: str) -> dict:
    doc = _col(db).find_one({"supplier_id": supplier_id.strip().upper()})
    if doc is None:
        raise NotFoundError(f"Supplier '{supplier_id}' does not exist.")
    return doc


def supplier_exists(db: Database, supplier_id: str) -> bool:
    return _col(db).count_documents({"supplier_id": supplier_id}, limit=1) == 1


def list_suppliers(db: Database, search: Optional[str] = None) -> list:
    query: dict = {}
    if search and search.strip():
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        query = {"$or": [{"supplier_id": rx}, {"name": rx}, {"city": rx}, {"contact_person": rx}]}
    return list(_col(db).find(query).sort("supplier_id", 1))


def update_supplier(db: Database, supplier_id: str, /, **changes) -> dict:
    unknown = set(changes) - set(_EDITABLE)
    if unknown:
        raise v.InputValidationError(f"Cannot update field(s): {', '.join(sorted(unknown))}.")
    cleaned = {}
    if "name" in changes:
        cleaned["name"] = v.clean_text(changes["name"], "Supplier name")
    if "contact_person" in changes:
        cleaned["contact_person"] = v.clean_text(changes["contact_person"], "Contact person", False)
    if "phone" in changes:
        cleaned["phone"] = v.clean_phone(changes["phone"])
    if "email" in changes:
        cleaned["email"] = v.clean_email(changes["email"])
    if "city" in changes:
        cleaned["city"] = v.clean_text(changes["city"], "City", required=False)
    if not cleaned:
        raise v.InputValidationError("No changes supplied.")
    with translate_write_errors("Duplicate value."):
        result = _col(db).update_one({"supplier_id": supplier_id.strip().upper()}, {"$set": cleaned})
    if result.matched_count == 0:
        raise NotFoundError(f"Supplier '{supplier_id}' does not exist.")
    return get_supplier(db, supplier_id)


def delete_supplier(db: Database, supplier_id: str) -> None:
    """Business rule: a supplier that still supplies products cannot be deleted."""
    supplier_id = supplier_id.strip().upper()
    count = db[config.COLLECTION_PRODUCTS].count_documents({"supplier_id": supplier_id})
    if count:
        raise DeletionBlockedError(
            f"Supplier '{supplier_id}' supplies {count} product(s). Reassign or remove them first.")
    result = _col(db).delete_one({"supplier_id": supplier_id})
    if result.deleted_count == 0:
        raise NotFoundError(f"Supplier '{supplier_id}' does not exist.")
