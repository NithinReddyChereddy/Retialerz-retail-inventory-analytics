"""Validation tests: pure Python helpers (no DB) + MongoDB $jsonSchema rejection (real DB)."""
from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError, WriteError

import config
from services import validation as v
from services.errors import DuplicateError, InputValidationError, NotFoundError
from services.product_service import create_product
from services.supplier_service import create_supplier

NOW = datetime.now(timezone.utc)


# ---------- Python-side validators (no database needed) ----------
@pytest.mark.parametrize("email", ["a@b.com", "first.last+tag@shop.example.co.in"])
def test_valid_emails(email):
    assert v.clean_email(email) == email


@pytest.mark.parametrize("email", ["plain", "a@b", "@x.com", "a b@x.com"])
def test_invalid_emails(email):
    with pytest.raises(InputValidationError):
        v.clean_email(email)


@pytest.mark.parametrize("phone", ["+91-555-0101", "(022) 555 0102", "9876543210"])
def test_valid_phones(phone):
    assert v.clean_phone(phone) == phone


@pytest.mark.parametrize("phone", ["abc", "123", "+1-555-CALL-NOW", "1" * 20])
def test_invalid_phones(phone):
    with pytest.raises(InputValidationError):
        v.clean_phone(phone)


@pytest.mark.parametrize("bad", [-1, -0.01, "10", None, True, float("nan"), float("inf")])
def test_invalid_price_rejected(bad):
    with pytest.raises(InputValidationError):
        v.clean_price(bad)


@pytest.mark.parametrize("bad", [-1, 2.5, "3", None, True])
def test_invalid_stock_integer_rejected(bad):
    with pytest.raises(InputValidationError):
        v.clean_int(bad, "Quantity")


def test_blank_names_rejected():
    with pytest.raises(InputValidationError):
        v.clean_text("   ", "Name")


# ---------- Service-level rejection (real DB) ----------
def test_service_rejects_negative_price_and_stock(db, supplier):
    with pytest.raises(InputValidationError):
        create_product(db, "X-1", "X", "Cat", "SUP-T1", -5, 1, 1)
    with pytest.raises(InputValidationError):
        create_product(db, "X-2", "X", "Cat", "SUP-T1", 5, -1, 1)
    assert db[config.COLLECTION_PRODUCTS].count_documents({}) == 0


def test_duplicate_sku_rejected(db, product):
    with pytest.raises(DuplicateError, match="TST-001"):
        create_product(db, "tst-001", "Other", "Gadgets", "SUP-T1", 1.0)


def test_duplicate_supplier_rejected(db, supplier):
    with pytest.raises(DuplicateError):
        create_supplier(db, "SUP-T1", "Dup")


def test_product_requires_existing_supplier(db):
    with pytest.raises(NotFoundError, match="NOPE"):
        create_product(db, "Y-1", "Y", "Cat", "NOPE", 1.0)


def test_unique_indexes_exist(db):
    assert "uq_sku" in db[config.COLLECTION_PRODUCTS].index_information()
    assert db[config.COLLECTION_PRODUCTS].index_information()["uq_sku"]["unique"]
    assert db[config.COLLECTION_SUPPLIERS].index_information()["uq_supplier_id"]["unique"]
    assert db[config.COLLECTION_MOVEMENTS].index_information()["uq_movement_id"]["unique"]


def test_raw_duplicate_sku_blocked_by_index(db, product):
    doc = dict(db[config.COLLECTION_PRODUCTS].find_one({"sku": "TST-001"}, {"_id": 0}))
    with pytest.raises(DuplicateKeyError):
        db[config.COLLECTION_PRODUCTS].insert_one(doc)


# ---------- MongoDB's OWN validator rejects bad documents (bypassing all Python checks) ----------
def _good_product():
    return {"sku": "RAW-1", "name": "Raw", "category": "C", "supplier_id": "SUP-T1",
            "unit_price": 1.5, "quantity_in_stock": 3, "reorder_level": 1,
            "created_at": NOW, "updated_at": NOW}


def test_validators_are_active_and_reject_mode(db):
    for info in db.list_collections():
        assert info["options"]["validationAction"] == "error"
        assert info["options"]["validationLevel"] == "strict"
        assert "$jsonSchema" in info["options"]["validator"]


def test_valid_raw_document_is_accepted(db):
    assert db[config.COLLECTION_PRODUCTS].insert_one(_good_product()).inserted_id


@pytest.mark.parametrize("patch", [
    {"unit_price": -1},                      # negative price
    {"quantity_in_stock": -3},               # negative stock
    {"quantity_in_stock": 2.5},              # non-integer stock
    {"reorder_level": -1},
    {"name": ""},                            # empty name
    {"name": "   "},                         # blank name
    {"unit_price": "free"},                  # wrong type
    {"created_at": "2026-01-01"},            # date string instead of BSON Date
])
def test_mongodb_rejects_invalid_product(db, patch):
    doc = {**_good_product(), **patch}
    with pytest.raises(WriteError) as exc:
        db[config.COLLECTION_PRODUCTS].insert_one(doc)
    assert exc.value.code == 121  # DocumentValidationFailure


def test_mongodb_rejects_missing_required_field(db):
    doc = _good_product()
    del doc["reorder_level"]
    with pytest.raises(WriteError) as exc:
        db[config.COLLECTION_PRODUCTS].insert_one(doc)
    assert exc.value.code == 121


def _mov(**kw):
    base = {"movement_id": "M-1", "sku": "RAW-1", "movement_type": "IN", "quantity": 5,
            "reason": "test", "movement_date": NOW}
    base.update(kw)
    return base


@pytest.mark.parametrize("patch", [
    {"movement_type": "SIDEWAYS"},
    {"movement_type": "IN", "quantity": -5},
    {"movement_type": "OUT", "quantity": 0},
    {"movement_type": "ADJUSTMENT", "quantity": 0},
    {"quantity": 1.5},
    {"reason": ""},
    {"movement_date": "yesterday"},
])
def test_mongodb_rejects_invalid_movement(db, patch):
    with pytest.raises(WriteError) as exc:
        db[config.COLLECTION_MOVEMENTS].insert_one(_mov(**patch))
    assert exc.value.code == 121


def test_mongodb_accepts_signed_adjustment(db):
    db[config.COLLECTION_MOVEMENTS].insert_one(_mov(movement_type="ADJUSTMENT", quantity=-4))


def test_mongodb_rejects_supplier_without_name(db):
    with pytest.raises(WriteError):
        db[config.COLLECTION_SUPPLIERS].insert_one({"supplier_id": "S-1", "name": ""})
