"""Kiểm tra kết nối và trạng thái cơ bản của database dùng chung.

Chỉ đọc dữ liệu; không tạo, sửa hoặc xóa bảng/bản ghi.
"""
from __future__ import annotations

import os
import sys

import mysql.connector
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    config = {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ.get("DB_PORT", "3306")),
        "database": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "connection_timeout": 5,
    }
    connection = mysql.connector.connect(**config)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT DATABASE() AS database_name, VERSION() AS version")
        info = cursor.fetchone()
        print(f"Kết nối thành công: {info['database_name']} ({info['version']})")
        checks = {
            "products": "SELECT COUNT(*) AS total FROM products",
            "product_variants": "SELECT COUNT(*) AS total FROM product_variants",
            "inventory": "SELECT COUNT(*) AS total FROM inventory",
            "customers": "SELECT COUNT(*) AS total FROM users WHERE user_type = 'customer'",
            "orders": "SELECT COUNT(*) AS total FROM orders",
        }
        for name, query in checks.items():
            cursor.execute(query)
            print(f"{name}: {cursor.fetchone()['total']}")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyError as exc:
        print(f"Thiếu biến môi trường: {exc.args[0]}", file=sys.stderr)
        raise SystemExit(1)
    except mysql.connector.Error as exc:
        print(f"Không kết nối được database ({exc.__class__.__name__}, mã {exc.errno}).", file=sys.stderr)
        raise SystemExit(1)
