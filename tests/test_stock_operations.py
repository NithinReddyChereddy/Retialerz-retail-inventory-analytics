"""Stock IN / OUT / ADJUSTMENT, atomicity, concurrency and consistency (real MongoDB)."""
import threading

import pytest

import config
from services import analytics_service as an
from services import product_service as ps
from services import stock_service as ss
from services.errors import (InputValidationError, InsufficientStockError, NotFoundError,
                             StockConsistencyError)


def _qty(db, sku="TST-001"):
    return db[config.COLLECTION_PRODUCTS].find_one({"sku": sku})["quantity_in_stock"]


def test_stock_in_increases_stock_and_records_movement(db, product):
    res = ss.stock_in(db, "TST-001", 15, "Supplier delivery")
    assert (res["previous_quantity"], res["quantity_in_stock"]) == (20, 35)
    assert _qty(db) == 35
    m = db[config.COLLECTION_MOVEMENTS].find_one({"movement_id": res["movement"]["movement_id"]})
    assert m["movement_type"] == "IN" and m["quantity"] == 15 and m["sku"] == "TST-001"


def test_stock_out_decreases_stock_and_records_movement(db, product):
    res = ss.stock_out(db, "TST-001", 8, "Sale")
    assert res["quantity_in_stock"] == 12 and _qty(db) == 12
    assert db[config.COLLECTION_MOVEMENTS].count_documents({"sku": "TST-001", "movement_type": "OUT"}) == 1


def test_stock_out_exactly_all_stock_allowed(db, product):
    ss.stock_out(db, "TST-001", 20, "Clearance")
    assert _qty(db) == 0


def test_stock_out_more_than_available_rejected_and_nothing_recorded(db, product):
    before = db[config.COLLECTION_MOVEMENTS].count_documents({})
    with pytest.raises(InsufficientStockError, match="20 available"):
        ss.stock_out(db, "TST-001", 21, "Too many")
    assert _qty(db) == 20
    assert db[config.COLLECTION_MOVEMENTS].count_documents({}) == before


def test_movement_for_unknown_product_rejected(db):
    with pytest.raises(NotFoundError):
        ss.stock_in(db, "GHOST", 1, "x")


@pytest.mark.parametrize("bad", [0, -2, 1.5, "3", None, True])
def test_in_out_require_positive_integer(db, product, bad):
    with pytest.raises(InputValidationError):
        ss.stock_in(db, "TST-001", bad, "x")
    with pytest.raises(InputValidationError):
        ss.stock_out(db, "TST-001", bad, "x")


def test_reason_required(db, product):
    with pytest.raises(InputValidationError):
        ss.stock_in(db, "TST-001", 1, "  ")


def test_adjustment_positive_and_negative(db, product):
    assert ss.adjust_stock(db, "TST-001", 4, "Found in storage")["quantity_in_stock"] == 24
    assert ss.adjust_stock(db, "TST-001", -9, "Damaged")["quantity_in_stock"] == 15
    kinds = db[config.COLLECTION_MOVEMENTS].distinct("movement_type", {"sku": "TST-001"})
    assert "ADJUSTMENT" in kinds


def test_adjustment_zero_rejected(db, product):
    with pytest.raises(InputValidationError, match="zero"):
        ss.adjust_stock(db, "TST-001", 0, "nothing")


def test_adjustment_that_makes_stock_negative_rejected(db, product):
    with pytest.raises(InsufficientStockError):
        ss.adjust_stock(db, "TST-001", -21, "too much")
    assert _qty(db) == 20


def test_stock_matches_movement_history(db, product):
    ss.stock_in(db, "TST-001", 10, "a")
    ss.stock_out(db, "TST-001", 7, "b")
    ss.adjust_stock(db, "TST-001", -2, "c")
    assert an.stock_consistency_mismatches(db) == []
    assert _qty(db) == 20 + 10 - 7 - 2


def test_consistency_check_detects_tampering(db, product):
    db[config.COLLECTION_PRODUCTS].update_one({"sku": "TST-001"}, {"$inc": {"quantity_in_stock": 5}})
    bad = an.stock_consistency_mismatches(db)
    assert bad == [{"sku": "TST-001", "quantity_in_stock": 25, "stock_from_history": 20}]


def test_concurrent_stock_outs_never_go_negative(db, product):
    """30 threads each try to remove 1 unit from 20 -> exactly 20 succeed, 10 are rejected."""
    results = {"ok": 0, "rejected": 0, "other": []}
    lock = threading.Lock()

    def worker():
        try:
            ss.stock_out(db, "TST-001", 1, "race")
            with lock:
                results["ok"] += 1
        except InsufficientStockError:
            with lock:
                results["rejected"] += 1
        except Exception as exc:  # pragma: no cover
            with lock:
                results["other"].append(repr(exc))

    threads = [threading.Thread(target=worker) for _ in range(30)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results["other"] == []
    assert (results["ok"], results["rejected"]) == (20, 10)
    assert _qty(db) == 0
    assert an.stock_consistency_mismatches(db) == []


def test_compensation_when_movement_insert_fails(db, product, monkeypatch):
    """Standalone-mongod strategy: if the movement insert fails, the stock change is reversed
    and the caller gets an error (never a false success)."""
    monkeypatch.setattr(ss, "supports_transactions", lambda _c: False)
    orig = ss.build_movement

    def bad_movement(*a, **k):
        m = orig(*a, **k)
        m["reason"] = ""          # MongoDB's validator will reject this insert
        return m

    monkeypatch.setattr(ss, "build_movement", bad_movement)
    with pytest.raises(StockConsistencyError, match="rolled back"):
        ss.stock_out(db, "TST-001", 5, "will fail")
    assert _qty(db) == 20
    assert an.stock_consistency_mismatches(db) == []


@pytest.mark.requires_transactions
def test_transaction_rolls_back_stock_if_movement_fails(db, product, has_transactions, monkeypatch):
    if not has_transactions:
        pytest.skip("Deployment does not support transactions (standalone mongod).")
    orig = ss.build_movement

    def bad_movement(*a, **k):
        m = orig(*a, **k)
        m["reason"] = ""
        return m

    monkeypatch.setattr(ss, "build_movement", bad_movement)
    with pytest.raises(Exception):
        ss.stock_in(db, "TST-001", 5, "will fail")
    assert _qty(db) == 20


def test_opening_stock_creates_matching_movement(db, supplier):
    ps.create_product(db, "OPEN-1", "Opened", "C", "SUP-T1", 1.0, 12, 2)
    mv = list(db[config.COLLECTION_MOVEMENTS].find({"sku": "OPEN-1"}))
    assert len(mv) == 1 and mv[0]["quantity"] == 12 and mv[0]["movement_type"] == "IN"
    assert an.stock_consistency_mismatches(db) == []


def test_list_movements_newest_first_and_filtered(db, product):
    ss.stock_in(db, "TST-001", 1, "first")
    ss.stock_out(db, "TST-001", 1, "second")
    rows = ss.list_movements(db, "TST-001")
    assert rows[0]["reason"] == "second" and len(rows) == 3
