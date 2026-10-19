"""Stock operations: IN, OUT and ADJUSTMENT.

Consistency strategy
--------------------
1. The stock change is ONE atomic conditional update on the product document
   (``find_one_and_update`` with a ``quantity_in_stock >= needed`` filter and ``$inc``).
   MongoDB applies the filter + increment atomically, so concurrent stock-outs can never
   drive stock below zero.
2. If the deployment supports multi-document transactions (replica set / Atlas), the
   product update and the movement insert run in ONE transaction (all-or-nothing).
3. On a standalone mongod (no transactions) a documented COMPENSATION strategy is used:
   update stock first, then insert the movement; if the insert fails the stock change is
   reversed with an inverse ``$inc``. If even the reversal fails a StockConsistencyError
   is raised that names the SKU. The caller is never told an operation succeeded unless
   BOTH the stock update and the movement record were written.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo import DESCENDING, ReturnDocument
from pymongo.database import Database

import config
from database.connection import supports_transactions
from services import validation as v
from services._mongo import translate_write_errors
from services.errors import InsufficientStockError, NotFoundError, StockConsistencyError


def new_movement_id() -> str:
    return f"MOV-{uuid.uuid4().hex[:12].upper()}"


def build_movement(sku: str, movement_type: str, quantity: int, reason: str,
                   movement_date: Optional[datetime] = None) -> dict:
    return {
        "movement_id": new_movement_id(),
        "sku": sku,
        "movement_type": movement_type,
        "quantity": quantity,
        "reason": reason,
        "movement_date": movement_date or datetime.now(timezone.utc),
    }


def _conditional_update(db: Database, sku: str, delta: int, session=None) -> dict:
    """Atomically apply delta to stock; refuse if the result would be negative."""
    products = db[config.COLLECTION_PRODUCTS]
    query: dict = {"sku": sku}
    if delta < 0:
        # Atomic guard: only match if enough stock exists RIGHT NOW.
        query["quantity_in_stock"] = {"$gte": -delta}
    updated = products.find_one_and_update(
        query,
        {"$inc": {"quantity_in_stock": delta},
         "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )
    if updated is not None:
        return updated
    current = products.find_one({"sku": sku}, {"quantity_in_stock": 1}, session=session)
    if current is None:
        raise NotFoundError(f"Product '{sku}' does not exist.")
    raise InsufficientStockError(
        f"Insufficient stock for '{sku}': {current['quantity_in_stock']} available, "
        f"change of {delta:+d} would make stock negative.")


def _record(db: Database, sku: str, movement_type: str, quantity: int, reason: str,
            movement_date: Optional[datetime] = None) -> dict:
    sku = v.clean_identifier(sku, "SKU")
    reason = v.clean_text(reason, "Reason")
    if movement_type in ("IN", "OUT"):
        quantity = v.clean_int(quantity, "Quantity", minimum=1)
    else:
        quantity = v.clean_int(quantity, "Adjustment quantity", minimum=None)
        if quantity == 0:
            raise v.InputValidationError("Adjustment quantity cannot be zero.")
    delta = -quantity if movement_type == "OUT" else quantity

    # Python-side referential check: the product must exist.
    if db[config.COLLECTION_PRODUCTS].count_documents({"sku": sku}, limit=1) == 0:
        raise NotFoundError(f"Product '{sku}' does not exist; cannot record a stock movement.")

    movement = build_movement(sku, movement_type, quantity, reason, movement_date)
    client = db.client
    movements = db[config.COLLECTION_MOVEMENTS]

    if supports_transactions(client):
        result: dict = {}

        def txn(session):
            result["product"] = _conditional_update(db, sku, delta, session)
            movements.insert_one(dict(movement), session=session)

        with client.start_session() as session:
            with translate_write_errors("Duplicate movement id."):
                session.with_transaction(txn)
        product = result["product"]
    else:
        product = _conditional_update(db, sku, delta)
        try:
            with translate_write_errors("Duplicate movement id."):
                movements.insert_one(dict(movement))
        except Exception as exc:
            _compensate(db, sku, delta, exc)
            raise StockConsistencyError(
                f"Movement NOT recorded for '{sku}'; the stock change was rolled back. "
                f"Cause: {exc}") from exc

    return {"movement": movement, "sku": sku,
            "previous_quantity": product["quantity_in_stock"] - delta,
            "quantity_in_stock": product["quantity_in_stock"]}


def _compensate(db: Database, sku: str, delta: int, cause: Exception) -> None:
    """Reverse a stock change after a failed movement insert (non-transaction path)."""
    query: dict = {"sku": sku}
    if -delta < 0:
        query["quantity_in_stock"] = {"$gte": delta}
    try:
        res = db[config.COLLECTION_PRODUCTS].update_one(query, {"$inc": {"quantity_in_stock": -delta}})
        if res.matched_count == 0:
            raise RuntimeError("stock changed concurrently, inverse update did not match")
    except Exception as comp_exc:
        raise StockConsistencyError(
            f"CRITICAL: movement insert failed for '{sku}' AND rollback failed ({comp_exc}). "
            f"Stock for this SKU may be off by {delta:+d}; run the consistency check. "
            f"Original cause: {cause}") from comp_exc


def stock_in(db: Database, sku: str, quantity: int, reason: str,
             movement_date: Optional[datetime] = None) -> dict:
    return _record(db, sku, "IN", quantity, reason, movement_date)


def stock_out(db: Database, sku: str, quantity: int, reason: str,
              movement_date: Optional[datetime] = None) -> dict:
    return _record(db, sku, "OUT", quantity, reason, movement_date)


def adjust_stock(db: Database, sku: str, quantity: int, reason: str,
                 movement_date: Optional[datetime] = None) -> dict:
    """Signed adjustment (+ found stock, - loss/damage). Zero and negative results rejected."""
    return _record(db, sku, "ADJUSTMENT", quantity, reason, movement_date)


def list_movements(db: Database, sku: Optional[str] = None, limit: int = 50) -> list:
    query = {"sku": sku.strip().upper()} if sku else {}
    return list(db[config.COLLECTION_MOVEMENTS].find(query)
                .sort([("movement_date", DESCENDING), ("_id", DESCENDING)]).limit(limit))
