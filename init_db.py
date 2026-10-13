from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterator

import mysql.connector
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
SCHEMA_FILE = PROJECT_ROOT / "data" / "schema" / "honda_chatbot_rbac.sql"
SEED_FILE = PROJECT_ROOT / "data" / "seed" / "honda_import_data.sql"
EXPECTED_COUNTS = {
    "products": 10,
    "product_variants": 28,
    "inventory": 84,
    "customers": 80,
    "customer_profiles": 80,
    "orders": 30,
}


def get_config() -> dict[str, object]:
    load_dotenv(PROJECT_ROOT / ".env")
    required = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "CHATBOT_RO_PASSWORD",
    )
    missing = [name for name in required if os.getenv(name) is None]
    if missing:
        raise RuntimeError(f"Thiếu biến môi trường: {', '.join(missing)}")

    database = os.environ["DB_NAME"]
    if database != "honda_chatbot":
        raise RuntimeError("DB_NAME phải là honda_chatbot khi chạy script khởi tạo schema")

    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "chatbot_ro_password": os.environ["CHATBOT_RO_PASSWORD"],
        "database": database,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }


def split_sql_script(script: str) -> Iterator[str]:
    statement: list[str] = []
    quote: str | None = None
    line_comment = False
    block_comment = False
    index = 0

    while index < len(script):
        char = script[index]
        next_char = script[index + 1] if index + 1 < len(script) else ""

        if line_comment:
            statement.append(char)
            if char in "\r\n":
                line_comment = False
            index += 1
            continue

        if block_comment:
            statement.append(char)
            if char == "*" and next_char == "/":
                statement.append(next_char)
                block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote:
            statement.append(char)
            if char == "\\" and next_char:
                statement.append(next_char)
                index += 2
                continue
            if char == quote:
                if next_char == quote:
                    statement.append(next_char)
                    index += 2
                    continue
                quote = None
            index += 1
            continue

        if char in "'\"`":
            quote = char
            statement.append(char)
            index += 1
            continue

        if char == "#" or (char == "-" and next_char == "-" and (index + 2 == len(script) or script[index + 2].isspace())):
            line_comment = True
            statement.append(char)
            if char == "-":
                statement.append(next_char)
                index += 2
            else:
                index += 1
            continue

        if char == "/" and next_char == "*":
            block_comment = True
            statement.extend((char, next_char))
            index += 2
            continue

        if char == ";":
            sql = "".join(statement).strip()
            if sql:
                yield sql
            statement = []
        else:
            statement.append(char)
        index += 1

    sql = "".join(statement).strip()
    if sql:
        yield sql


def connect(config: dict[str, object], with_database: bool) -> mysql.connector.MySQLConnection:
    connection_config = dict(config)
    if not with_database:
        connection_config.pop("database")
    return mysql.connector.connect(**connection_config)


def execute_script(
    connection: mysql.connector.MySQLConnection,
    path: Path,
    replacements: dict[str, str] | None = None,
) -> None:
    script = path.read_text(encoding="utf-8")
    for marker, value in (replacements or {}).items():
        script = script.replace(marker, value.replace("\\", "\\\\").replace("'", "\\'"))
    cursor = connection.cursor()
    try:
        for statement in split_sql_script(script):
            cursor.execute(statement)
            if cursor.with_rows:
                cursor.fetchall()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def verify_counts(connection: mysql.connector.MySQLConnection) -> dict[str, int]:
    queries = {
        "products": ("SELECT COUNT(*) FROM products", ()),
        "product_variants": ("SELECT COUNT(*) FROM product_variants", ()),
        "inventory": ("SELECT COUNT(*) FROM inventory", ()),
        "customers": ("SELECT COUNT(*) FROM users WHERE id > %s", (100,)),
        "customer_profiles": ("SELECT COUNT(*) FROM customer_profiles", ()),
        "orders": ("SELECT COUNT(*) FROM orders", ()),
    }
    cursor = connection.cursor()
    try:
        counts: dict[str, int] = {}
        for name, (query, params) in queries.items():
            cursor.execute(query, params)
            counts[name] = int(cursor.fetchone()[0])
        return counts
    finally:
        cursor.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Khởi tạo schema và seed MySQL Honda.")
    parser.add_argument("--reset", action="store_true", help="Xóa và tạo lại database honda_chatbot.")
    args = parser.parse_args()

    if not args.reset:
        parser.error("Schema có DROP DATABASE; phải truyền --reset để thực hiện.")

    config = get_config()
    connection = None
    try:
        connection = connect(config, with_database=False)
        execute_script(connection, SCHEMA_FILE)
        connection.close()
        connection = connect(config, with_database=True)
        execute_script(connection, SEED_FILE)
        extension_dir = PROJECT_ROOT / "data" / "schema" / "extensions"
        for extension in sorted(extension_dir.glob("[0-9][0-9]_*.sql")):
            replacements = {}
            if extension.name == "03_chatbot_ro_user.sql":
                replacements["__CHATBOT_RO_PASSWORD__"] = str(config["chatbot_ro_password"])
            execute_script(connection, extension, replacements)
        counts = verify_counts(connection)
    except Exception as exc:
        if connection is not None and connection.is_connected():
            connection.close()
        safe_message = str(exc).replace(str(config.get("password", "")), "***")
        print(f"MySQL initialization failed: {safe_message}", file=sys.stderr)
        return 1
    finally:
        if connection is not None and connection.is_connected():
            connection.close()

    print("MySQL schema and seed completed.")
    for name, actual in counts.items():
        expected = EXPECTED_COUNTS[name]
        print(f"{name}: {actual} (expected {expected})")
    if counts != EXPECTED_COUNTS:
        print("Count verification failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
