from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import MySQLConnection
from mysql.connector.pooling import MySQLConnectionPool


load_dotenv()
_APP_POOL: MySQLConnectionPool | None = None
_TEXT_SQL_POOL: MySQLConnectionPool | None = None


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Thiếu biến môi trường {name}")
    return value


def _base_config() -> dict[str, Any]:
    return {
        "host": _required("DB_HOST"),
        "port": int(_required("DB_PORT")),
        "database": _required("DB_NAME"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }


def _pool(role: str) -> MySQLConnectionPool:
    global _APP_POOL, _TEXT_SQL_POOL
    if role == "app" and _APP_POOL is not None:
        return _APP_POOL
    if role == "text_to_sql" and _TEXT_SQL_POOL is not None:
        return _TEXT_SQL_POOL
    config = _base_config()
    if role == "text_to_sql":
        config["user"] = os.getenv("CHATBOT_RO_USER", "chatbot_ro")
        config["password"] = _required("CHATBOT_RO_PASSWORD")
        pool_name = "honda_text_sql_pool"
    else:
        config["user"] = _required("DB_USER")
        config["password"] = _required("DB_PASSWORD")
        pool_name = "honda_app_pool"
    pool = MySQLConnectionPool(pool_name=pool_name, pool_size=5, **config)
    if role == "text_to_sql":
        _TEXT_SQL_POOL = pool
    else:
        _APP_POOL = pool
    return pool


def get_connection(role: str = "app") -> MySQLConnection:
    if role not in {"app", "text_to_sql"}:
        raise ValueError("role phải là app hoặc text_to_sql")
    return _pool(role).get_connection()


@contextmanager
def cursor(role: str = "app", dictionary: bool = True) -> Iterator[Any]:
    connection = get_connection(role)
    db_cursor = connection.cursor(dictionary=dictionary)
    try:
        yield db_cursor
    finally:
        db_cursor.close()
        connection.close()


def execute_write(query: str, params: tuple[Any, ...] = ()) -> None:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(query, params)
        db_cursor.connection.commit()
