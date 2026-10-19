"""Index creation and one-call schema initialisation (idempotent, creates NO data)."""
from pymongo import ASCENDING
from pymongo.database import Database

import config
from database.validators import apply_validators


def create_indexes(db: Database) -> None:
    # Unique indexes required by the assignment.
    db[config.COLLECTION_PRODUCTS].create_index([("sku", ASCENDING)], unique=True, name="uq_sku")
    db[config.COLLECTION_SUPPLIERS].create_index(
        [("supplier_id", ASCENDING)], unique=True, name="uq_supplier_id")
    db[config.COLLECTION_MOVEMENTS].create_index(
        [("movement_id", ASCENDING)], unique=True, name="uq_movement_id")
    # Non-unique helper indexes that speed up lookups, filters and $lookup joins.
    db[config.COLLECTION_PRODUCTS].create_index("category", name="ix_category")
    db[config.COLLECTION_PRODUCTS].create_index("supplier_id", name="ix_supplier_ref")
    db[config.COLLECTION_MOVEMENTS].create_index("sku", name="ix_movement_sku")


def initialize_database(db: Database) -> None:
    """Validators + indexes. Safe to run repeatedly; inserts no documents."""
    apply_validators(db)
    create_indexes(db)
