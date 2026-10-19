"""CRUD + connection + referential-integrity tests (real MongoDB)."""
import pytest

import config
from database.connection import DatabaseConnectionError, get_client
from services import product_service as ps
from services import stock_service as ss
from services import supplier_service as sup
from services.errors import DeletionBlockedError, InputValidationError, NotFoundError


def test_connection_succeeds(client):
    assert client.admin.command("ping")["ok"] == 1.0


def test_bad_uri_gives_helpful_error():
    with pytest.raises(DatabaseConnectionError, match="Cannot reach MongoDB"):
        import config as c
        old = c.SERVER_SELECTION_TIMEOUT_MS
        c.SERVER_SELECTION_TIMEOUT_MS = 300
        try:
            get_client("mongodb://127.0.0.1:1")
        finally:
            c.SERVER_SELECTION_TIMEOUT_MS = old


def test_three_collections_exist(db):
    assert {config.COLLECTION_PRODUCTS, config.COLLECTION_SUPPLIERS,
            config.COLLECTION_MOVEMENTS} <= set(db.list_collection_names())


# ---------------- Suppliers ----------------
def test_supplier_crud_cycle(db):
    created = sup.create_supplier(db, "sup-x", "Temp Supplier", "Ann", "+1-555-0199", "a@x.com", "Pune")
    assert created["supplier_id"] == "SUP-X"
    assert sup.get_supplier(db, "SUP-X")["name"] == "Temp Supplier"                    # Read
    assert [s["supplier_id"] for s in sup.list_suppliers(db, "temp")] == ["SUP-X"]     # Search
    updated = sup.update_supplier(db, "SUP-X", city="Jaipur", phone="+1-555-0111")     # Update
    assert updated["city"] == "Jaipur"
    sup.delete_supplier(db, "SUP-X")                                                   # Delete
    with pytest.raises(NotFoundError):
        sup.get_supplier(db, "SUP-X")


def test_supplier_rejects_bad_email_and_phone(db):
    with pytest.raises(InputValidationError):
        sup.create_supplier(db, "S2", "Name", email="nope")
    with pytest.raises(InputValidationError):
        sup.create_supplier(db, "S3", "Name", phone="abc")


def test_cannot_delete_supplier_with_products(db, product):
    with pytest.raises(DeletionBlockedError, match="supplies 1 product"):
        sup.delete_supplier(db, "SUP-T1")


# ---------------- Products ----------------
def test_product_crud_cycle_with_temporary_record(db, supplier):
    p = ps.create_product(db, "tmp-1", "Temp Item", "Temp", "SUP-T1", 9.99)           # Create
    assert p["sku"] == "TMP-1" and p["quantity_in_stock"] == 0
    assert ps.get_product(db, "TMP-1")["name"] == "Temp Item"                          # Read
    upd = ps.update_product(db, "TMP-1", name="Temp Item v2", unit_price=12.5)         # Update
    assert upd["name"] == "Temp Item v2" and upd["unit_price"] == 12.5
    assert upd["updated_at"] >= upd["created_at"]
    ps.delete_product(db, "TMP-1")                                                     # Delete
    with pytest.raises(NotFoundError):
        ps.get_product(db, "TMP-1")


def test_dates_are_real_bson_dates(db, product):
    from datetime import datetime
    raw = db[config.COLLECTION_PRODUCTS].find_one({"sku": "TST-001"})
    assert isinstance(raw["created_at"], datetime) and isinstance(raw["updated_at"], datetime)
    assert db[config.COLLECTION_PRODUCTS].count_documents({"created_at": {"$type": "date"}}) == 1


def test_update_cannot_change_quantity_or_sku(db, product):
    with pytest.raises(InputValidationError, match="stock operations"):
        ps.update_product(db, "TST-001", quantity_in_stock=999)
    with pytest.raises(InputValidationError):
        ps.update_product(db, "TST-001", sku="NEW")


def test_update_product_checks_supplier_reference(db, product):
    with pytest.raises(NotFoundError):
        ps.update_product(db, "TST-001", supplier_id="GHOST")


def test_update_missing_product(db):
    with pytest.raises(NotFoundError):
        ps.update_product(db, "NOPE", name="x")


def test_list_search_and_filters(db, supplier):
    ps.create_product(db, "A-1", "Apple Juice", "Drinks", "SUP-T1", 2, 50, 10)   # normal
    ps.create_product(db, "A-2", "Apple Sauce", "Food", "SUP-T1", 2, 5, 10)      # low
    ps.create_product(db, "B-1", "Bread", "Food", "SUP-T1", 1, 0, 10)            # out
    assert [p["sku"] for p in ps.list_products(db, search="apple")] == ["A-1", "A-2"]
    assert [p["sku"] for p in ps.list_products(db, category="Food")] == ["A-2", "B-1"]
    assert [p["sku"] for p in ps.list_products(db, stock_status="normal")] == ["A-1"]
    assert [p["sku"] for p in ps.list_products(db, stock_status="low")] == ["A-2"]
    assert [p["sku"] for p in ps.list_products(db, stock_status="out_of_stock")] == ["B-1"]
    assert [p["sku"] for p in ps.list_products(db, search="apple", category="Food")] == ["A-2"]
    assert ps.list_categories(db) == ["Drinks", "Food"]
    with pytest.raises(InputValidationError):
        ps.list_products(db, stock_status="bogus")


def test_search_treats_input_literally_not_as_regex(db, product):
    assert ps.list_products(db, search=".*") == []


def test_cannot_delete_product_with_movement_history(db, product):
    # 'product' fixture has opening stock 20 -> has an 'Opening stock' movement.
    with pytest.raises(DeletionBlockedError, match="stock movement"):
        ps.delete_product(db, "TST-001")
    assert ps.get_product(db, "TST-001")


def test_cannot_delete_product_after_manual_movement(db, supplier):
    ps.create_product(db, "Z-1", "Z", "C", "SUP-T1", 1.0)
    ss.stock_in(db, "Z-1", 3, "delivery")
    with pytest.raises(DeletionBlockedError):
        ps.delete_product(db, "Z-1")


def test_delete_missing_product(db):
    with pytest.raises(NotFoundError):
        ps.delete_product(db, "NOPE")
