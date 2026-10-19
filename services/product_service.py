"""Product CRUD with Python-side business rules."""
import re
from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database

import config
from database.connection import supports_transactions
from services import validation as v
from services._mongo import translate_write_errors
from services.errors import DeletionBlockedError, NotFoundError, StockConsistencyError
from services.stock_service import build_movement
from services.supplier_service import supplier_exists

STOCK_STATUSES = ("normal", "low", "out_of_stock")
_EDITABLE = ("name", "category", "supplier_id", "unit_price", "reorder_level")


def _col(db: Database):
    return db[config.COLLECTION_PRODUCTS]


def _require_supplier(db: Database, supplier_id: str) -> str:
    supplier_id = v.clean_identifier(supplier_id, "Supplier ID")
    if not supplier_exists(db, supplier_id):  # JSON Schema cannot check references
        raise NotFoundError(f"Supplier '{supplier_id}' does not exist; create it first.")
    return supplier_id


def create_product(db: Database, sku: str, name: str, category: str, supplier_id: str,
                   unit_price: float, quantity_in_stock: int = 0, reorder_level: int = 0) -> dict:
    """Create a product. Non-zero opening stock also writes an 'Opening stock' IN movement,
    so current stock always equals the sum of its movement history."""
    now = datetime.now(timezone.utc)
    doc = {
        "sku": v.clean_identifier(sku, "SKU"),
        "name": v.clean_text(name, "Product name"),
        "category": v.clean_text(category, "Category", max_len=60),
        "supplier_id": _require_supplier(db, supplier_id),
        "unit_price": v.clean_price(unit_price),
        "quantity_in_stock": v.clean_int(quantity_in_stock, "Quantity in stock"),
        "reorder_level": v.clean_int(reorder_level, "Reorder level"),
        "created_at": now,
        "updated_at": now,
    }
    movement = None
    if doc["quantity_in_stock"] > 0:
        movement = build_movement(doc["sku"], "IN", doc["quantity_in_stock"], "Opening stock", now)
    dup_msg = f"SKU '{doc['sku']}' already exists."
    client = db.client
    movements = db[config.COLLECTION_MOVEMENTS]

    if supports_transactions(client):
        def txn(session):
            _col(db).insert_one(dict(doc), session=session)
            if movement:
                movements.insert_one(dict(movement), session=session)

        with client.start_session() as session:
            with translate_write_errors(dup_msg):
                session.with_transaction(txn)
    else:
        with translate_write_errors(dup_msg):
            _col(db).insert_one(dict(doc))
        if movement:
            try:
                with translate_write_errors("Duplicate movement id."):
                    movements.insert_one(dict(movement))
            except Exception as exc:
                try:
                    _col(db).delete_one({"sku": doc["sku"]})  # compensation: undo the insert
                except Exception as comp_exc:
                    raise StockConsistencyError(
                        f"CRITICAL: product '{doc['sku']}' inserted but opening movement failed and "
                        f"rollback failed ({comp_exc}).") from exc
                raise StockConsistencyError(
                    f"Product '{doc['sku']}' was NOT created (opening-stock movement failed: {exc}).") from exc
    return _col(db).find_one({"sku": doc["sku"]})


def get_product(db: Database, sku: str) -> dict:
    doc = _col(db).find_one({"sku": sku.strip().upper()})
    if doc is None:
        raise NotFoundError(f"Product '{sku}' does not exist.")
    return doc


def list_products(db: Database, search: Optional[str] = None, category: Optional[str] = None,
                  stock_status: Optional[str] = None, supplier_id: Optional[str] = None) -> list:
    """List/search/filter. stock_status: normal (> reorder level), low (0 < qty <= reorder),
    out_of_stock (qty == 0)."""
    clauses: list = []
    if search and search.strip():
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        clauses.append({"$or": [{"sku": rx}, {"name": rx}]})
    if category:
        clauses.append({"category": category})
    if supplier_id:
        clauses.append({"supplier_id": supplier_id})
    if stock_status:
        if stock_status not in STOCK_STATUSES:
            raise v.InputValidationError(f"stock_status must be one of {STOCK_STATUSES}.")
        q, r = "$quantity_in_stock", "$reorder_level"
        clauses.append({
            "normal": {"$expr": {"$gt": [q, r]}},
            "low": {"$expr": {"$and": [{"$gt": [q, 0]}, {"$lte": [q, r]}]}},
            "out_of_stock": {"quantity_in_stock": 0},
        }[stock_status])
    query = {"$and": clauses} if clauses else {}
    return list(_col(db).find(query).sort("sku", 1))


def list_categories(db: Database) -> list:
    return sorted(_col(db).distinct("category"))


def update_product(db: Database, sku: str, /, **changes) -> dict:
    """Update descriptive fields. Stock quantity is deliberately NOT editable here: it may
    only change through stock movements so history and stock never diverge."""
    unknown = set(changes) - set(_EDITABLE)
    if unknown:
        raise v.InputValidationError(
            f"Cannot update field(s): {', '.join(sorted(unknown))}. "
            "Use stock operations to change quantity; SKU is immutable.")
    cleaned: dict = {}
    if "name" in changes:
        cleaned["name"] = v.clean_text(changes["name"], "Product name")
    if "category" in changes:
        cleaned["category"] = v.clean_text(changes["category"], "Category", max_len=60)
    if "supplier_id" in changes:
        cleaned["supplier_id"] = _require_supplier(db, changes["supplier_id"])
    if "unit_price" in changes:
        cleaned["unit_price"] = v.clean_price(changes["unit_price"])
    if "reorder_level" in changes:
        cleaned["reorder_level"] = v.clean_int(changes["reorder_level"], "Reorder level")
    if not cleaned:
        raise v.InputValidationError("No changes supplied.")
    cleaned["updated_at"] = datetime.now(timezone.utc)
    with translate_write_errors("Duplicate value."):
        result = _col(db).update_one({"sku": sku.strip().upper()}, {"$set": cleaned})
    if result.matched_count == 0:
        raise NotFoundError(f"Product '{sku}' does not exist.")
    return get_product(db, sku)


def delete_product(db: Database, sku: str) -> None:
    """Delete only products WITHOUT stock-movement history (audit trail must stay intact)."""
    sku = sku.strip().upper()
    history = db[config.COLLECTION_MOVEMENTS].count_documents({"sku": sku})
    if history:
        raise DeletionBlockedError(
            f"Product '{sku}' has {history} stock movement record(s). Deleting it would leave "
            "orphaned history and break stock auditing, so deletion is blocked.")
    if _col(db).delete_one({"sku": sku}).deleted_count == 0:
        raise NotFoundError(f"Product '{sku}' does not exist.")
