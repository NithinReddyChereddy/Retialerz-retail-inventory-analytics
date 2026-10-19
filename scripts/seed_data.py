"""Repeatable seed script (fictional data only).

Usage:
    python -m scripts.seed_data            # idempotent: inserts only what is missing
    python -m scripts.seed_data --reset --yes   # DROP the 3 collections, then re-seed

Product quantities are DERIVED from the movement list below, so current stock always
equals the net of its movement history (verified at the end by an aggregation pipeline).
Seeding is deliberately NOT run by the application at startup.
"""
import argparse
from datetime import datetime, timezone

from pymongo.database import Database

import config
from database.connection import DatabaseConnectionError, close_client, get_database
from database.indexes import initialize_database
from services.analytics_service import stock_consistency_mismatches

SUPPLIERS = [
    ("SUP-001", "Harbor Beverage Supply", "Meera Iyer", "+91-555-0101", "orders@harborbev.example.com", "Pune"),
    ("SUP-002", "Crispy Corner Foods", "Rahul Verma", "+91-555-0102", "sales@crispycorner.example.com", "Delhi"),
    ("SUP-003", "PaperTrail Stationers", "Sara Thomas", "+91-555-0103", "hello@papertrail.example.com", "Bengaluru"),
    ("SUP-004", "HomeNest Essentials", "Kabir Singh", "+91-555-0104", "trade@homenest.example.com", "Jaipur"),
    ("SUP-005", "PureCare Wholesale", "Nisha Patel", "+91-555-0105", "care@purecare.example.com", "Ahmedabad"),
]

# sku, name, category, supplier_id, unit_price, reorder_level, opening_stock
PRODUCTS = [
    ("BEV-001", "Orange Juice 1L", "Beverages", "SUP-001", 3.50, 20, 80),
    ("BEV-002", "Sparkling Water 500ml", "Beverages", "SUP-001", 1.20, 40, 150),
    ("BEV-003", "Green Tea Box (25 bags)", "Beverages", "SUP-001", 4.75, 15, 45),
    ("BEV-004", "Cold Coffee Can 250ml", "Beverages", "SUP-001", 2.10, 30, 90),
    ("SNK-001", "Salted Peanuts 200g", "Snacks", "SUP-002", 2.40, 25, 70),
    ("SNK-002", "Potato Chips Classic 150g", "Snacks", "SUP-002", 1.80, 30, 120),
    ("SNK-003", "Oat Cookies 300g", "Snacks", "SUP-002", 3.25, 20, 60),
    ("SNK-004", "Trail Mix 250g", "Snacks", "SUP-002", 4.90, 12, 30),
    ("STA-001", "A4 Notebook 200 pages", "Stationery", "SUP-003", 2.95, 25, 90),
    ("STA-002", "Gel Pen Blue", "Stationery", "SUP-003", 0.60, 100, 400),
    ("STA-003", "Sticky Notes Pack", "Stationery", "SUP-003", 1.75, 30, 100),
    ("STA-004", "Desk Stapler", "Stationery", "SUP-003", 6.50, 8, 25),
    ("HOU-001", "Dish Soap 500ml", "Household", "SUP-004", 3.10, 18, 55),
    ("HOU-002", "Kitchen Towels 2-roll", "Household", "SUP-004", 2.80, 20, 65),
    ("HOU-003", "LED Bulb 9W", "Household", "SUP-004", 3.99, 25, 80),
    ("HOU-004", "Reusable Shopping Bag", "Household", "SUP-004", 1.50, 40, 120),
    ("PCR-001", "Herbal Shampoo 250ml", "Personal Care", "SUP-005", 5.40, 15, 40),
    ("PCR-002", "Hand Wash 300ml", "Personal Care", "SUP-005", 2.65, 20, 60),
    ("PCR-003", "Toothpaste 100g", "Personal Care", "SUP-005", 1.95, 30, 110),
    ("PCR-004", "Bath Soap 3-pack", "Personal Care", "SUP-004", 3.30, 25, 75),
]

# (type, sku, quantity, reason, (month, day)) - everything after the opening stock
MOVEMENTS = [
    ("OUT", "BEV-001", 62, "Weekly sales", (9, 5)),
    ("OUT", "BEV-002", 60, "Weekly sales", (9, 6)),
    ("OUT", "BEV-003", 12, "Weekly sales", (9, 7)),
    ("OUT", "BEV-004", 35, "Weekly sales", (9, 8)),
    ("ADJUSTMENT", "BEV-004", -3, "Damaged cans written off", (9, 9)),
    ("OUT", "SNK-001", 20, "Weekly sales", (9, 10)),
    ("IN", "SNK-001", 40, "Supplier restock", (9, 15)),
    ("OUT", "SNK-002", 100, "Festival promotion sales", (9, 12)),
    ("OUT", "SNK-003", 18, "Weekly sales", (9, 13)),
    ("OUT", "SNK-004", 30, "Sold out - seasonal demand", (9, 14)),
    ("OUT", "STA-001", 25, "School season sales", (9, 16)),
    ("OUT", "STA-002", 320, "Bulk school order", (9, 17)),
    ("OUT", "STA-004", 10, "Weekly sales", (9, 18)),
    ("ADJUSTMENT", "STA-004", -2, "Display units removed", (9, 19)),
    ("OUT", "HOU-001", 20, "Weekly sales", (9, 20)),
    ("ADJUSTMENT", "HOU-001", 2, "Stock count correction (found)", (9, 21)),
    ("OUT", "HOU-002", 22, "Weekly sales", (9, 22)),
    ("ADJUSTMENT", "HOU-002", -1, "Torn packaging", (9, 23)),
    ("OUT", "HOU-003", 20, "Weekly sales", (9, 24)),
    ("OUT", "HOU-004", 90, "Eco-week promotion", (9, 25)),
    ("OUT", "HOU-004", 30, "Eco-week promotion", (9, 26)),
    ("OUT", "PCR-001", 15, "Weekly sales", (9, 27)),
    ("OUT", "PCR-002", 45, "Weekly sales", (9, 28)),
    ("OUT", "PCR-003", 30, "Weekly sales", (9, 29)),
    ("IN", "PCR-003", 25, "Supplier restock", (10, 2)),
]
SEED_YEAR = 2026


def _dt(month: int, day: int) -> datetime:
    return datetime(SEED_YEAR, month, day, 10, 0, tzinfo=timezone.utc)


def build_movements() -> list:
    opening_date = datetime(SEED_YEAR, 8, 1, 9, 0, tzinfo=timezone.utc)
    docs = []
    for i, p in enumerate(PRODUCTS, start=1):
        docs.append({"movement_id": f"MOV-{i:04d}", "sku": p[0], "movement_type": "IN",
                     "quantity": p[6], "reason": "Opening stock", "movement_date": opening_date})
    for j, (mtype, sku, qty, reason, (m, d)) in enumerate(MOVEMENTS, start=len(PRODUCTS) + 1):
        docs.append({"movement_id": f"MOV-{j:04d}", "sku": sku, "movement_type": mtype,
                     "quantity": qty, "reason": reason, "movement_date": _dt(m, d)})
    return docs


def build_products(movements: list) -> list:
    stock = {p[0]: 0 for p in PRODUCTS}
    for m in movements:  # derive final stock from history -> guaranteed consistency
        stock[m["sku"]] += -m["quantity"] if m["movement_type"] == "OUT" else m["quantity"]
    created = datetime(SEED_YEAR, 8, 1, 9, 0, tzinfo=timezone.utc)
    return [{"sku": s, "name": n, "category": c, "supplier_id": sup, "unit_price": price,
             "quantity_in_stock": stock[s], "reorder_level": r,
             "created_at": created, "updated_at": _dt(10, 2)}
            for (s, n, c, sup, price, r, _o) in PRODUCTS]


def seed(db: Database) -> dict:
    """Insert missing documents only ($setOnInsert upserts) -> safe to run repeatedly."""
    initialize_database(db)
    movements = build_movements()
    products = build_products(movements)
    suppliers = [{"supplier_id": a, "name": b, "contact_person": c, "phone": d, "email": e, "city": f}
                 for (a, b, c, d, e, f) in SUPPLIERS]
    inserted = {}
    for col, docs, key in ((config.COLLECTION_SUPPLIERS, suppliers, "supplier_id"),
                           (config.COLLECTION_PRODUCTS, products, "sku"),
                           (config.COLLECTION_MOVEMENTS, movements, "movement_id")):
        count = 0
        for d in docs:
            res = db[col].update_one({key: d[key]}, {"$setOnInsert": d}, upsert=True)
            count += 1 if res.upserted_id is not None else 0
        inserted[col] = count
    return inserted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="drop the three collections first")
    ap.add_argument("--yes", action="store_true", help="confirm --reset")
    args = ap.parse_args()
    try:
        db = get_database()
        if args.reset:
            if not args.yes:
                print("Refusing to drop data without --yes.")
                return 2
            for name in (config.COLLECTION_PRODUCTS, config.COLLECTION_SUPPLIERS, config.COLLECTION_MOVEMENTS):
                db.drop_collection(name)
            print("Dropped existing collections.")
        inserted = seed(db)
        print(f"Newly inserted documents: {inserted}")
        for col in (config.COLLECTION_SUPPLIERS, config.COLLECTION_PRODUCTS, config.COLLECTION_MOVEMENTS):
            print(f"  {col}: {db[col].count_documents({})} total")
        bad = stock_consistency_mismatches(db)
        print("Stock vs movement-history check:", "OK (all consistent)" if not bad else f"MISMATCH {bad}")
        return 0 if not bad else 1
    except DatabaseConnectionError as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        close_client()


if __name__ == "__main__":
    raise SystemExit(main())
