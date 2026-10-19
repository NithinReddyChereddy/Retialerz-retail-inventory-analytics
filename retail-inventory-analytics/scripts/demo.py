"""Scripted demonstration of the assignment's 11-step sequence (prints real MongoDB output).

Usage:  python -m scripts.demo            (run scripts.seed_data first)
        python -m scripts.demo --pause    (wait for Enter between steps, for screenshots)
Temporary records (DEMO-001) are created and deleted. Steps 7-9 add one real IN and one
real OUT movement to BEV-002, so counts change by 2 each time the demo is run.
"""
import argparse
import json
from datetime import datetime, timezone

from bson import json_util
from pymongo.errors import WriteError

import config
from database.connection import DatabaseConnectionError, close_client, get_client, get_database
from services import analytics_service as an
from services import product_service as ps
from services import stock_service as ss
from services import supplier_service as sup
from services.errors import AppError

PAUSE = False


def step(n: int, title: str) -> None:
    if PAUSE:
        input("\n[Enter to continue] ")
    print(f"\n{'=' * 78}\nSTEP {n}: {title}\n{'=' * 78}")


def show(obj) -> None:
    print(json.dumps(json.loads(json_util.dumps(obj)), indent=2, default=str))


def table(rows: list, cols: list) -> None:
    widths = [max(len(c), *(len(str(r.get(c, ''))) for r in rows)) if rows else len(c) for c in cols]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(r.get(c, '')).ljust(w) for c, w in zip(cols, widths)))


def main() -> int:
    global PAUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", action="store_true")
    PAUSE = ap.parse_args().pause
    try:
        step(1, "Connect to MongoDB")
        client = get_client()
        db = get_database()
        print("Server version:", client.server_info()["version"], "| database:", db.name)
        if db[config.COLLECTION_PRODUCTS].count_documents({}) == 0:
            print("Database is empty - run `python -m scripts.seed_data` first.")
            return 1

        step(2, "Show the three collections")
        for name in (config.COLLECTION_PRODUCTS, config.COLLECTION_SUPPLIERS, config.COLLECTION_MOVEMENTS):
            print(f"{name:16s} documents={db[name].count_documents({})}  "
                  f"indexes={list(db[name].index_information())}")

        step(3, "Insert and retrieve a product (temporary record DEMO-001)")
        if db[config.COLLECTION_PRODUCTS].count_documents({"sku": "DEMO-001"}):
            ps.delete_product(db, "DEMO-001")  # leftover from an interrupted earlier run
        ps.create_product(db, "DEMO-001", "Demo Notebook", "Stationery", "SUP-003", 4.25, 0, 5)
        show(ps.get_product(db, "DEMO-001"))

        step(4, "Update the product")
        show(ps.update_product(db, "DEMO-001", name="Demo Notebook (A5)", unit_price=4.75))

        step(5, "Delete the temporary record (allowed: it has no movement history)")
        ps.delete_product(db, "DEMO-001")
        print("DEMO-001 still exists?", bool(db[config.COLLECTION_PRODUCTS].count_documents({"sku": "DEMO-001"})))
        try:
            ps.delete_product(db, "BEV-001")
        except AppError as exc:
            print("Deleting BEV-001 (has history) refused ->", exc)

        step(6, "MongoDB itself rejects invalid data (bypassing all Python checks)")
        bad = {"sku": "BAD-1", "name": "Bad", "category": "X", "supplier_id": "SUP-001", "unit_price": -5,
               "quantity_in_stock": -2, "reorder_level": 1,
               "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        try:
            db[config.COLLECTION_PRODUCTS].insert_one(bad)
            db[config.COLLECTION_PRODUCTS].delete_one({"sku": "BAD-1"})  # clean up the stray row
            print("UNEXPECTED: invalid document was accepted - validators are NOT active! "
                  "Run `python -m scripts.init_db` and check the MongoDB version/permissions.")
            return 1
        except WriteError as exc:
            print(f"WriteError code={exc.code} (DocumentValidationFailure)")
            print("Message:", exc.details.get("errmsg"))
        try:
            ps.create_product(db, "BEV-001", "Duplicate", "Beverages", "SUP-001", 1.0)
        except AppError as exc:
            print("Duplicate SKU ->", exc)

        step(7, "Stock IN: BEV-002 +25")
        r = ss.stock_in(db, "BEV-002", 25, "Demo: supplier delivery")
        print(f"stock {r['previous_quantity']} -> {r['quantity_in_stock']}  movement {r['movement']['movement_id']}")

        step(8, "Valid stock OUT: BEV-002 -10")
        r = ss.stock_out(db, "BEV-002", 10, "Demo: counter sales")
        print(f"stock {r['previous_quantity']} -> {r['quantity_in_stock']}  movement {r['movement']['movement_id']}")

        step(9, "Invalid stock OUT (more than available) is rejected")
        try:
            ss.stock_out(db, "BEV-002", 100000, "Demo: impossible sale")
        except AppError as exc:
            print("REJECTED ->", exc)
        print("Stock unchanged:", ps.get_product(db, "BEV-002")["quantity_in_stock"])

        step(10, "Aggregation pipelines (computed inside MongoDB)")
        print("\nPipeline 1 - Low-stock products")
        table(an.low_stock_products(db), ["sku", "name", "category", "available_quantity", "reorder_level"])
        print("\nPipeline 2 - Estimated inventory value by category (at current selling prices)")
        table(an.inventory_value_by_category(db), ["category", "total_units", "estimated_inventory_value", "distinct_products"])
        print("\nPipeline 3 - Stock movement by category")
        table(an.stock_movement_by_category(db), ["category", "movement_count", "total_in_quantity",
                                                  "total_out_quantity", "net_adjustment_quantity"])
        print("\nPipeline 4 - Supplier inventory summary")
        table(an.supplier_inventory_summary(db), ["supplier_id", "supplier_name", "product_count", "estimated_inventory_value"])
        print("\nStock-vs-history mismatches:", an.stock_consistency_mismatches(db) or "none")

        step(11, "Now open the Streamlit app (streamlit run app.py) -> Dashboard and Analytics pages")
        return 0
    except DatabaseConnectionError as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        close_client()


if __name__ == "__main__":
    raise SystemExit(main())
