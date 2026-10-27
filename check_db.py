# Kiểm tra kết nối MySQL và đếm các bảng nghiệp vụ chính từ dòng lệnh.
from __future__ import annotations

import os  # Đọc thông tin kết nối từ biến môi trường.
import sys  # Ghi lỗi cấu hình/kết nối ra stderr và trả mã thoát.

import mysql.connector  # Mở kết nối MySQL và nhận lỗi driver.
from dotenv import load_dotenv  # Nạp file .env trước khi đọc credential.


def main() -> int:
    # Đọc thông tin server/schema rồi kiểm tra số dòng của các bảng trọng yếu.
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
    # Terminal Windows có thể dùng cp1252; xuất UTF-8 để in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except KeyError as exc:
        print(f"Thiếu biến môi trường: {exc.args[0]}", file=sys.stderr)
        raise SystemExit(1)
    except mysql.connector.Error as exc:
        print(f"Không kết nối được database ({exc.__class__.__name__}, mã {exc.errno}).", file=sys.stderr)
        raise SystemExit(1)
