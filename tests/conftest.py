"""Integration-test fixtures: tests run against a REAL MongoDB test database.

If MongoDB is unreachable the DB tests are SKIPPED (never reported as passed).
The test database name differs from the application database; it is dropped between tests.
"""
import os

import pytest

import config
from database.connection import DatabaseConnectionError, get_client, supports_transactions
from database.indexes import initialize_database

TEST_URI = os.environ.get("MONGODB_TEST_URI", config.MONGODB_URI)


@pytest.fixture(scope="session")
def client():
    if config.TEST_DB_NAME == config.DB_NAME:
        pytest.exit("MONGODB_TEST_DB_NAME must differ from MONGODB_DB_NAME", returncode=2)
    try:
        c = get_client(TEST_URI)
    except DatabaseConnectionError as exc:
        pytest.skip(f"MongoDB not reachable - integration tests skipped: {exc}")
    yield c
    c.close()


@pytest.fixture()
def db(client):
    """A clean, schema-initialised test database for every test."""
    database = client[config.TEST_DB_NAME]
    for name in (config.COLLECTION_PRODUCTS, config.COLLECTION_SUPPLIERS, config.COLLECTION_MOVEMENTS):
        database.drop_collection(name)
    initialize_database(database)
    yield database
    client.drop_database(config.TEST_DB_NAME)


@pytest.fixture()
def supplier(db):
    from services.supplier_service import create_supplier
    return create_supplier(db, "SUP-T1", "Test Supplier", "Tess Ter", "+1-555-0100",
                           "tess@example.com", "Testville")


@pytest.fixture()
def product(db, supplier):
    from services.product_service import create_product
    return create_product(db, "TST-001", "Test Widget", "Gadgets", "SUP-T1", 10.0, 20, 5)


@pytest.fixture()
def has_transactions(client):
    return supports_transactions(client)
