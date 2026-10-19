"""All four mandatory aggregation pipelines against hand-calculated expectations (real MongoDB)."""
from datetime import datetime, timezone

import pytest

import config
from services import analytics_service as an
from services import product_service as ps
from services import stock_service as ss
from services import supplier_service as sup


@pytest.fixture()
def data(db):
    """Small scenario whose answers are calculated by hand below.

    SKU   cat  sup  price qty reorder
    P1    Food S1   2.00  10  4      value 20.00   normal
    P2    Food S1   5.00  3   3      value 15.00   low (==)
    P3    Tech S2   100   0   2      value  0.00   low (zero)
    P4    Tech S2   50    4   1      value 200.00  normal
    """
    sup.create_supplier(db, "S1", "Supplier One", city="Pune")
    sup.create_supplier(db, "S2", "Supplier Two", city="Delhi")
    ps.create_product(db, "P1", "P one", "Food", "S1", 2.0, 10, 4)
    ps.create_product(db, "P2", "P two", "Food", "S1", 5.0, 3, 3)
    ps.create_product(db, "P3", "P three", "Tech", "S2", 100.0, 0, 2)
    ps.create_product(db, "P4", "P four", "Tech", "S2", 50.0, 4, 1)
    # Extra movements on top of 3 opening-stock IN movements (P1:10, P2:3, P4:4):
    ss.stock_in(db, "P3", 6, "restock")           # P3 -> 6
    ss.stock_out(db, "P3", 6, "sold")             # P3 -> 0
    ss.stock_out(db, "P1", 2, "sold")             # P1 -> 8  (value 16)
    ss.adjust_stock(db, "P4", -1, "damaged")      # P4 -> 3  (value 150)
    ss.adjust_stock(db, "P2", 2, "found")         # P2 -> 5  (value 25)
    return db
    # Final: P1 8@2=16 | P2 5@5=25 | P3 0 | P4 3@50=150  (P2 now above reorder 3, P1 above 4)


def test_pipeline1_low_stock(data):
    rows = an.low_stock_products(data)
    # Only P3 (0 <= 2) is low now; P2 was raised to 5 > 3.
    assert rows == [{"sku": "P3", "name": "P three", "category": "Tech",
                     "available_quantity": 0, "reorder_level": 2}]


def test_pipeline1_includes_equal_to_reorder_level(data):
    ss.stock_out(data, "P2", 2, "sold")  # P2 5 -> 3 == reorder level 3
    skus = [r["sku"] for r in an.low_stock_products(data)]
    assert skus == ["P3", "P2"]  # sorted by available quantity ascending


def test_pipeline2_inventory_value_by_category(data):
    rows = an.inventory_value_by_category(data)
    assert rows == [
        {"category": "Tech", "total_units": 3, "estimated_inventory_value": 150.0, "distinct_products": 2},
        {"category": "Food", "total_units": 13, "estimated_inventory_value": 41.0, "distinct_products": 2},
    ]


def test_pipeline3_movement_by_category(data):
    rows = {r["category"]: r for r in an.stock_movement_by_category(data)}
    # Food: opening IN 10 (P1) + opening IN 3 (P2); OUT 2 (P1); ADJ +2 (P2)  -> 4 movements
    assert rows["Food"] == {"category": "Food", "movement_count": 4, "total_in_quantity": 13,
                            "total_out_quantity": 2, "net_adjustment_quantity": 2, "adjustment_count": 1}
    # Tech: opening IN 4 (P4), IN 6 (P3), OUT 6 (P3), ADJ -1 (P4) -> 4 movements
    assert rows["Tech"] == {"category": "Tech", "movement_count": 4, "total_in_quantity": 10,
                            "total_out_quantity": 6, "net_adjustment_quantity": -1, "adjustment_count": 1}


def test_pipeline3_ordered_by_movement_count(data):
    ss.stock_in(data, "P1", 1, "extra")  # Food now has 5 movements
    assert [r["category"] for r in an.stock_movement_by_category(data)] == ["Food", "Tech"]


def test_pipeline4_supplier_summary(data):
    rows = an.supplier_inventory_summary(data)
    assert rows == [
        {"supplier_id": "S2", "supplier_name": "Supplier Two", "city": "Delhi",
         "product_count": 2, "estimated_inventory_value": 150.0},
        {"supplier_id": "S1", "supplier_name": "Supplier One", "city": "Pune",
         "product_count": 2, "estimated_inventory_value": 41.0},
    ]


def test_dashboard_summary(data):
    assert an.dashboard_summary(data) == {
        "total_products": 4, "total_units": 16, "estimated_inventory_value": 191.0, "low_stock_count": 1}


def test_dashboard_on_empty_database(db):
    assert an.dashboard_summary(db)["total_products"] == 0
    assert an.low_stock_products(db) == []


def test_seed_script_is_idempotent_and_consistent(db):
    from scripts.seed_data import seed
    first = seed(db)
    second = seed(db)
    assert first == {"suppliers": 5, "products": 20, "stock_movements": 45}
    assert second == {"suppliers": 0, "products": 0, "stock_movements": 0}
    assert db[config.COLLECTION_PRODUCTS].count_documents({}) == 20
    assert an.stock_consistency_mismatches(db) == []
    assert len(an.low_stock_products(db)) == 6
    assert db[config.COLLECTION_PRODUCTS].count_documents({"quantity_in_stock": 0}) == 2
    assert {r["category"] for r in an.inventory_value_by_category(db)} >= {"Beverages", "Snacks", "Stationery", "Household"}
