from __future__ import annotations

import sqlite3
import threading

_connection: sqlite3.Connection | None = None
_lock = threading.Lock()


def init_connection() -> sqlite3.Connection:
    global _connection
    _connection = sqlite3.connect(":memory:", check_same_thread=False)
    _connection.row_factory = sqlite3.Row
    return _connection


def get_connection() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("DB connection not initialized")
    return _connection


def get_lock() -> threading.Lock:
    return _lock


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
