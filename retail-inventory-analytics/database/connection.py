"""MongoDB connection handling (PyMongo only)."""
from __future__ import annotations

from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError, PyMongoError, ServerSelectionTimeoutError

import config

_client: Optional[MongoClient] = None
_txn_support: Optional[bool] = None


class DatabaseConnectionError(RuntimeError):
    """Raised with a human-friendly message when MongoDB cannot be reached."""


def _redact(uri: str) -> str:
    """Hide any credentials before showing the URI in an error message."""
    if "@" in uri and "://" in uri:
        scheme, rest = uri.split("://", 1)
        return f"{scheme}://***:***@{rest.split('@', 1)[1]}"
    return uri


def get_client(uri: Optional[str] = None) -> MongoClient:
    """Return a shared MongoClient, verifying connectivity with a ping."""
    global _client
    if _client is not None and uri is None:
        return _client
    target = uri or config.MONGODB_URI
    try:
        # tz_aware=True -> BSON Dates come back as timezone-aware UTC datetimes.
        client = MongoClient(
            target,
            serverSelectionTimeoutMS=config.SERVER_SELECTION_TIMEOUT_MS,
            tz_aware=True,
        )
        client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        raise DatabaseConnectionError(
            f"Cannot reach MongoDB at {_redact(target)}. Is the MongoDB service running "
            "(local) or is your IP allow-listed (Atlas)? Check MONGODB_URI."
        ) from exc
    except (ConfigurationError, PyMongoError) as exc:
        raise DatabaseConnectionError(
            f"MongoDB connection failed for {_redact(target)}: {exc}. "
            "Check the MONGODB_URI value and credentials."
        ) from exc
    if uri is None:
        _client = client
    return client


def get_database(name: Optional[str] = None, client: Optional[MongoClient] = None) -> Database:
    return (client or get_client())[name or config.DB_NAME]


def close_client() -> None:
    """Close the shared client (call on application exit)."""
    global _client, _txn_support
    if _client is not None:
        _client.close()
    _client = None
    _txn_support = None


def supports_transactions(client: MongoClient) -> bool:
    """Multi-document transactions need a replica set or sharded cluster.

    A standalone local mongod does NOT support them; Atlas always does.
    """
    global _txn_support
    if _txn_support is None:
        try:
            hello = client.admin.command("hello")
            _txn_support = bool(hello.get("setName") or hello.get("msg") == "isdbgrid")
        except PyMongoError:
            _txn_support = False
    return _txn_support
