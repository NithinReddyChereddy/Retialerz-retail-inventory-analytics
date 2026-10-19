"""MongoDB $jsonSchema validators (database-level validation).

Validation action = "error" and level = "strict": invalid inserts/updates are REJECTED.
Note: JSON Schema cannot enforce references between collections (sku / supplier_id);
those are checked in the Python service layer.
"""
from pymongo.database import Database
from pymongo.errors import CollectionInvalid

import config

_NUMBER = ["int", "long", "double", "decimal"]
_INTEGER = ["int", "long"]
_NON_BLANK = "\\S"  # regex: at least one non-whitespace character

PRODUCTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["sku", "name", "category", "supplier_id", "unit_price",
                     "quantity_in_stock", "reorder_level", "created_at", "updated_at"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "sku": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "name": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "category": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "supplier_id": {"bsonType": "string", "minLength": 1},
            "unit_price": {"bsonType": _NUMBER, "minimum": 0},
            "quantity_in_stock": {"bsonType": _INTEGER, "minimum": 0},
            "reorder_level": {"bsonType": _INTEGER, "minimum": 0},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

SUPPLIERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["supplier_id", "name"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "supplier_id": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "name": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "contact_person": {"bsonType": "string"},
            "phone": {"bsonType": "string"},
            "email": {"bsonType": "string"},
            "city": {"bsonType": "string"},
        },
    }
}

MOVEMENTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["movement_id", "sku", "movement_type", "quantity", "reason", "movement_date"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "movement_id": {"bsonType": "string", "minLength": 1},
            "sku": {"bsonType": "string", "minLength": 1},
            "movement_type": {"enum": list(config.MOVEMENT_TYPES)},
            # Integer, never zero (signed values allowed; sign rules in anyOf below).
            "quantity": {"bsonType": _INTEGER, "not": {"enum": [0]}},
            "reason": {"bsonType": "string", "minLength": 1, "pattern": _NON_BLANK},
            "movement_date": {"bsonType": "date"},
        },
        # IN / OUT must be positive; ADJUSTMENT may be negative or positive.
        "anyOf": [
            {"properties": {"movement_type": {"enum": ["IN", "OUT"]}, "quantity": {"minimum": 1}}},
            {"properties": {"movement_type": {"enum": ["ADJUSTMENT"]}}},
        ],
    }
}

SCHEMAS = {
    config.COLLECTION_PRODUCTS: PRODUCTS_SCHEMA,
    config.COLLECTION_SUPPLIERS: SUPPLIERS_SCHEMA,
    config.COLLECTION_MOVEMENTS: MOVEMENTS_SCHEMA,
}


def apply_validators(db: Database) -> None:
    """Create each collection with its validator, or collMod it if it already exists."""
    for name, schema in SCHEMAS.items():
        try:
            db.create_collection(name, validator=schema, validationLevel="strict",
                                 validationAction="error")
        except CollectionInvalid:  # already exists -> update its validator in place
            db.command("collMod", name, validator=schema, validationLevel="strict",
                       validationAction="error")
