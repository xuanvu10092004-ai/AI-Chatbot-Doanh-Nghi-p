# File này quản lý kết nối MySQL và cung cấp cursor/transaction dùng chung cho các module nghiệp vụ.
# Tách pool app và text-to-SQL để tài khoản read-only không ghi dữ liệu.
from __future__ import annotations

import os  # Đọc tên database, user và mật khẩu từ biến môi trường.
import time  # Chờ ngắn khi connection pool tạm thời hết kết nối.
from threading import Lock  # Bảo vệ thao tác khởi tạo pool dùng chung.
from pathlib import Path  # Tạo đường dẫn tới file .env.
from contextlib import contextmanager  # Cho phép dùng cursor và transaction với with.
from contextvars import ContextVar  # Lưu connection transaction riêng cho từng request.
from uuid import uuid4
from typing import Any, Iterator  # Mô tả kiểu dữ liệu dùng trong file.

import mysql.connector  # Driver thực hiện kết nối và chạy lệnh MySQL.
from dotenv import load_dotenv  # Nạp cấu hình cục bộ từ file .env.
from mysql.connector import MySQLConnection  # Kiểu connection mà driver trả về.
from mysql.connector.pooling import MySQLConnectionPool  # Pool giúp các request dùng lại connection.
from mysql.connector.errors import PoolError  # Báo pool tạm thời không có connection rảnh.


# Nạp file .env nằm cạnh source; giá trị bí mật không ghi trong mã.
load_dotenv(Path(__file__).resolve().parent / '.env')
# Tách pool app và text-to-SQL để tài khoản read-only không ghi dữ liệu.
_APP_POOL: MySQLConnectionPool | None = None
_TEXT_SQL_POOL: MySQLConnectionPool | None = None
_POOL_LOCK = Lock()
# Lưu connection transaction đang mở cho các cursor lồng trong cùng request.
_TRANSACTION = ContextVar('app_transaction',default=None)


# Kiểm tra biến môi trường bắt buộc trước khi dùng nó tạo connection.
def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Thiếu biến môi trường {name}")
    return value


# Gom thông số chung của MySQL; credential được thêm riêng theo role.
def _base_config() -> dict[str, Any]:
    return {
        "host": _required("DB_HOST"),
        "port": int(_required("DB_PORT")),
        "database": _required("DB_NAME"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "connection_timeout": 5,
    }


# Dùng khóa để hai request không khởi tạo trùng một connection pool.
def _pool(role: str) -> MySQLConnectionPool:
    with _POOL_LOCK:
        return _get_or_create_pool(role)


# Tái sử dụng pool đã có; nếu chưa có thì chọn credential theo role và tạo một lần.
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


# Chỉ cho phép role app hoặc text-to-SQL để không dùng nhầm quyền kết nối.
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
    # Nhánh này dùng chatbot_ro và đặt timeout cho truy vấn do LLM sinh.
    if role == 'text_to_sql':
        try:
            with connection.cursor() as cur:
                cur.execute('SET @ai_branch = NULL')
                cur.execute('SET @ai_user = NULL')
                # MySQL và MariaDB dùng tên timeout khác nhau, nên cần biết loại server.
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
# Cursor độc lập tự commit/rollback; cursor trong transaction dùng connection của transaction cha.
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
# Gom nhiều thao tác ghi để một lỗi có thể rollback toàn bộ thay đổi.
def transaction():
    """Một transaction cho công cụ và trạng thái xác nhận; cursor lồng không tự commit."""
    if _TRANSACTION.get() is not None:
        # A dialogue may catch a tool error and commit its clarification/audit.
        connection=_TRANSACTION.get()
        savepoint='tool_'+uuid4().hex
        with connection.cursor() as cur:cur.execute('SAVEPOINT '+savepoint)
        try:
            yield
        except Exception:
            with connection.cursor() as cur:cur.execute('ROLLBACK TO SAVEPOINT '+savepoint)
            raise
        finally:
            with connection.cursor() as cur:cur.execute('RELEASE SAVEPOINT '+savepoint)
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


# Dùng parameter binding cho giá trị động; context manager sẽ lo commit hoặc rollback.
def execute_write(query: str, params: tuple[Any, ...] = ()) -> None:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(query, params)
