"""Create collections, JSON Schema validators and indexes (NO data inserted).

Usage:  python -m scripts.init_db
"""
from database.connection import DatabaseConnectionError, close_client, get_database
from database.indexes import initialize_database
import config


def main() -> int:
    try:
        db = get_database()
        initialize_database(db)
        print(f"Database '{db.name}' initialised. Collections: {sorted(db.list_collection_names())}")
        for name, info in ((c['name'], c) for c in db.list_collections()):
            opts = info.get("options", {})
            print(f"  - {name}: validationAction={opts.get('validationAction')}, "
                  f"validationLevel={opts.get('validationLevel')}")
        return 0
    except DatabaseConnectionError as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        close_client()


if __name__ == "__main__":
    raise SystemExit(main())
