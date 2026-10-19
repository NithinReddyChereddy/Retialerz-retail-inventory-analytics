"""Aggregation pipelines. All calculations are done INSIDE MongoDB, not in Python.

Operator cheat-sheet (used in the comments below):
  $match   - filter documents (like SQL WHERE)
  $project - choose / rename / compute output fields (like SELECT)
  $group   - bucket documents by a key and compute accumulators (like GROUP BY)
  $sum     - add numbers (accumulator in $group, or expression on an array)
  $multiply- multiply values (quantity x price)
  $lookup  - left-outer join with another collection (like SQL LEFT JOIN)
  $unwind  - turn the joined array into one document per element
  $cond    - if/then/else expression (conditional value)
  $sort    - order the results (1 = ascending, -1 = descending)
"""
from pymongo.database import Database

import config

# --------------------------------------------------------------------------------------
# Pipeline 1 - Low-stock products (quantity_in_stock <= reorder_level)
# --------------------------------------------------------------------------------------
LOW_STOCK_PIPELINE = [
    # $match + $expr: compare TWO fields of the same document (qty <= reorder level).
    {"$match": {"$expr": {"$lte": ["$quantity_in_stock", "$reorder_level"]}}},
    # $project: return only the requested fields, renaming quantity_in_stock.
    {"$project": {"_id": 0, "sku": 1, "name": 1, "category": 1,
                  "available_quantity": "$quantity_in_stock", "reorder_level": 1}},
    # $sort: most urgent (lowest stock) first, SKU as tie-breaker.
    {"$sort": {"available_quantity": 1, "sku": 1}},
]

# --------------------------------------------------------------------------------------
# Pipeline 2 - Estimated inventory value by category (at CURRENT SELLING PRICES)
# --------------------------------------------------------------------------------------
INVENTORY_BY_CATEGORY_PIPELINE = [
    # $group by category. $sum adds units; $sum over $multiply adds qty x price per product;
    # $addToSet collects the distinct SKUs so we can count distinct products.
    {"$group": {
        "_id": "$category",
        "total_units": {"$sum": "$quantity_in_stock"},
        "estimated_inventory_value": {
            "$sum": {"$multiply": ["$quantity_in_stock", "$unit_price"]}},
        "skus": {"$addToSet": "$sku"},
    }},
    # $project: rename _id -> category, count distinct SKUs with $size, round money to 2 dp.
    {"$project": {"_id": 0, "category": "$_id", "total_units": 1,
                  "estimated_inventory_value": {"$round": ["$estimated_inventory_value", 2]},
                  "distinct_products": {"$size": "$skus"}}},
    # $sort: highest value first.
    {"$sort": {"estimated_inventory_value": -1, "category": 1}},
]

# --------------------------------------------------------------------------------------
# Pipeline 3 - Stock movement by category (runs on stock_movements)
# --------------------------------------------------------------------------------------
MOVEMENT_BY_CATEGORY_PIPELINE = [
    # $lookup: join each movement to its product on sku (movement.sku = product.sku).
    {"$lookup": {"from": config.COLLECTION_PRODUCTS, "localField": "sku",
                 "foreignField": "sku", "as": "product"}},
    # $unwind: flatten the 1-element 'product' array so product.category is addressable.
    {"$unwind": "$product"},
    # $group by the product's category. $cond picks the quantity only for the matching
    # movement type (otherwise 0), so ONE pass yields IN, OUT and ADJUSTMENT totals separately.
    {"$group": {
        "_id": "$product.category",
        "movement_count": {"$sum": 1},
        "total_in_quantity": {"$sum": {"$cond": [{"$eq": ["$movement_type", "IN"]}, "$quantity", 0]}},
        "total_out_quantity": {"$sum": {"$cond": [{"$eq": ["$movement_type", "OUT"]}, "$quantity", 0]}},
        "net_adjustment_quantity": {"$sum": {
            "$cond": [{"$eq": ["$movement_type", "ADJUSTMENT"]}, "$quantity", 0]}},
        "adjustment_count": {"$sum": {
            "$cond": [{"$eq": ["$movement_type", "ADJUSTMENT"]}, 1, 0]}},
    }},
    # $project: tidy field names.
    {"$project": {"_id": 0, "category": "$_id", "movement_count": 1, "total_in_quantity": 1,
                  "total_out_quantity": 1, "net_adjustment_quantity": 1, "adjustment_count": 1}},
    # $sort by number of movements (busiest category first).
    {"$sort": {"movement_count": -1, "category": 1}},
]

# --------------------------------------------------------------------------------------
# Pipeline 4 - Supplier inventory summary (runs on products)
# --------------------------------------------------------------------------------------
SUPPLIER_SUMMARY_PIPELINE = [
    # $lookup: join each product to its supplier on supplier_id.
    {"$lookup": {"from": config.COLLECTION_SUPPLIERS, "localField": "supplier_id",
                 "foreignField": "supplier_id", "as": "supplier"}},
    # $unwind: one document per product+supplier; keep products even if supplier is missing.
    {"$unwind": {"path": "$supplier", "preserveNullAndEmptyArrays": True}},
    # $group by supplier_id: count products and sum qty x price (estimated value).
    {"$group": {
        "_id": "$supplier_id",
        "supplier_name": {"$first": {"$ifNull": ["$supplier.name", "(unknown supplier)"]}},
        "city": {"$first": {"$ifNull": ["$supplier.city", ""]}},
        "product_count": {"$sum": 1},
        "estimated_inventory_value": {
            "$sum": {"$multiply": ["$quantity_in_stock", "$unit_price"]}},
    }},
    {"$project": {"_id": 0, "supplier_id": "$_id", "supplier_name": 1, "city": 1,
                  "product_count": 1,
                  "estimated_inventory_value": {"$round": ["$estimated_inventory_value", 2]}}},
    {"$sort": {"estimated_inventory_value": -1, "supplier_id": 1}},
]

# --------------------------------------------------------------------------------------
# Dashboard totals (single $group over products)
# --------------------------------------------------------------------------------------
DASHBOARD_PIPELINE = [
    {"$group": {
        "_id": None,  # one group for the whole collection
        "total_products": {"$sum": 1},
        "total_units": {"$sum": "$quantity_in_stock"},
        "estimated_inventory_value": {"$sum": {"$multiply": ["$quantity_in_stock", "$unit_price"]}},
        # $cond: count 1 for each low-stock product, 0 otherwise.
        "low_stock_count": {"$sum": {"$cond": [
            {"$lte": ["$quantity_in_stock", "$reorder_level"]}, 1, 0]}},
    }},
    {"$project": {"_id": 0, "total_products": 1, "total_units": 1, "low_stock_count": 1,
                  "estimated_inventory_value": {"$round": ["$estimated_inventory_value", 2]}}},
]

# --------------------------------------------------------------------------------------
# Consistency check: current stock must equal the signed sum of its movement history
# --------------------------------------------------------------------------------------
CONSISTENCY_PIPELINE = [
    {"$lookup": {"from": config.COLLECTION_MOVEMENTS, "localField": "sku",
                 "foreignField": "sku", "as": "movements"}},
    # $addFields + $reduce: walk the joined movements, adding +qty for IN/ADJUSTMENT and
    # -qty for OUT (via $cond) to a running total ($$value).
    {"$addFields": {"stock_from_history": {"$reduce": {
        "input": "$movements", "initialValue": 0,
        "in": {"$add": ["$$value", {"$cond": [{"$eq": ["$$this.movement_type", "OUT"]},
                                              {"$multiply": ["$$this.quantity", -1]},
                                              "$$this.quantity"]}]}}}}},
    # $match only products where the two numbers disagree.
    {"$match": {"$expr": {"$ne": ["$quantity_in_stock", "$stock_from_history"]}}},
    {"$project": {"_id": 0, "sku": 1, "quantity_in_stock": 1, "stock_from_history": 1}},
    {"$sort": {"sku": 1}},
]


def _run(db: Database, collection: str, pipeline: list) -> list:
    return list(db[collection].aggregate(pipeline))


def low_stock_products(db: Database) -> list:
    return _run(db, config.COLLECTION_PRODUCTS, LOW_STOCK_PIPELINE)


def inventory_value_by_category(db: Database) -> list:
    return _run(db, config.COLLECTION_PRODUCTS, INVENTORY_BY_CATEGORY_PIPELINE)


def stock_movement_by_category(db: Database) -> list:
    return _run(db, config.COLLECTION_MOVEMENTS, MOVEMENT_BY_CATEGORY_PIPELINE)


def supplier_inventory_summary(db: Database) -> list:
    return _run(db, config.COLLECTION_PRODUCTS, SUPPLIER_SUMMARY_PIPELINE)


def dashboard_summary(db: Database) -> dict:
    rows = _run(db, config.COLLECTION_PRODUCTS, DASHBOARD_PIPELINE)
    return rows[0] if rows else {"total_products": 0, "total_units": 0,
                                 "estimated_inventory_value": 0, "low_stock_count": 0}


def stock_consistency_mismatches(db: Database) -> list:
    """Empty list == every product's stock equals the net of its movement history."""
    return _run(db, config.COLLECTION_PRODUCTS, CONSISTENCY_PIPELINE)
