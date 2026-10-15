from __future__ import annotations

import os
import time
from threading import Lock
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import MySQLConnection
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector.errors import PoolError


load_dotenv(Path(__file__).resolve().parent / '.env')
_APP_POOL: MySQLConnectionPool | None = None
_TEXT_SQL_POOL: MySQLConnectionPool | None = None
_POOL_LOCK = Lock()
_TRANSACTION = ContextVar('app_transaction',default=None)


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
        "connection_timeout": 5,
    }


def _pool(role: str) -> MySQLConnectionPool:
    with _POOL_LOCK:
        return _get_or_create_pool(role)


def _get_or_create_pool(role: str) -> MySQLConnectionPool:
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
    pool = _pool(role)
    # Dashboard tải nhiều API cùng lúc; chờ kết nối được trả về thay vì làm
    # request chat đang đến đồng thời thất bại ngay khi cả 5 kết nối bận.
    deadline = time.monotonic() + 5
    while True:
        try:
            connection = pool.get_connection()
            break
        except PoolError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)
    if role == 'text_to_sql':
        try:
            with connection.cursor() as cur:
                cur.execute('SET @ai_branch = NULL')
                cur.execute('SET @ai_user = NULL')
                cur.execute('SELECT VERSION()')
                version = cur.fetchone()[0]
                if 'MariaDB' in version:
                    cur.execute('SET SESSION max_statement_time = %s', (5,))
                else:
                    cur.execute('SET SESSION MAX_EXECUTION_TIME = %s', (5000,))
        except Exception:
            connection.close()
            raise
    return connection


@contextmanager
def cursor(role: str = "app", dictionary: bool = True) -> Iterator[Any]:
    shared = _TRANSACTION.get() if role=='app' else None
    connection = shared or get_connection(role)
    db_cursor = None
    try:
        db_cursor = connection.cursor(dictionary=dictionary)
        yield db_cursor
        if shared is None:connection.commit()
    except Exception:
        if shared is None:connection.rollback()
        raise
    finally:
        if db_cursor is not None:
            db_cursor.close()
        if shared is None:connection.close()


@contextmanager
def transaction():
    """Một transaction cho công cụ và trạng thái xác nhận; cursor lồng không tự commit."""
    if _TRANSACTION.get() is not None:
        yield
        return
    connection=get_connection('app')
    token=_TRANSACTION.set(connection)
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _TRANSACTION.reset(token)
        connection.close()


def execute_write(query: str, params: tuple[Any, ...] = ()) -> None:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(query, params)
