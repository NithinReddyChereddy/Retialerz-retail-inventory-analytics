"""Central configuration. All secrets come from environment variables."""
import os

try:  # optional: load a local .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# Connection string is NEVER hard-coded with credentials.
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "retail_inventory")
TEST_DB_NAME = os.environ.get("MONGODB_TEST_DB_NAME", "retail_inventory_test")
SERVER_SELECTION_TIMEOUT_MS = int(os.environ.get("MONGODB_TIMEOUT_MS", "5000"))
CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "$")

COLLECTION_PRODUCTS = "products"
COLLECTION_SUPPLIERS = "suppliers"
COLLECTION_MOVEMENTS = "stock_movements"
MOVEMENT_TYPES = ("IN", "OUT", "ADJUSTMENT")
