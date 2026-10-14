from __future__ import annotations

import argparse
import os
import re
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
        "APP_DB_PASSWORD",
        "DEMO_ACCOUNT_PASSWORD",
    )
    missing = [name for name in required if os.getenv(name) is None]
    if missing:
        raise RuntimeError(f"Thiếu biến môi trường: {', '.join(missing)}")
    if len(os.environ['DEMO_ACCOUNT_PASSWORD'])<10:
        raise RuntimeError('DEMO_ACCOUNT_PASSWORD must contain at least 10 characters')

    database = os.environ["DB_NAME"]
    if database != "honda_chatbot":
        raise RuntimeError("DB_NAME phải là honda_chatbot khi chạy script khởi tạo schema")

    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "user": os.getenv('ADMIN_DB_USER', os.environ["DB_USER"]),
        "password": os.getenv('ADMIN_DB_PASSWORD', os.environ["DB_PASSWORD"]),
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
    connection_config.pop("chatbot_ro_password", None)
    if not with_database:
        connection_config.pop("database")
    return mysql.connector.connect(**connection_config)


def execute_script(
    connection: mysql.connector.MySQLConnection,
    path: Path,
    skip_database_drop: bool = False,
) -> None:
    script = path.read_text(encoding="utf-8")
    cursor = connection.cursor()
    try:
        for statement in split_sql_script(script):
            executable = re.sub(r"--[^\n]*|/\*.*?\*/", "", statement, flags=re.S).strip()
            if skip_database_drop and executable.upper().startswith("DROP DATABASE"):
                continue
            cursor.execute(statement)
            if cursor.with_rows:
                cursor.fetchall()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def apply_extensions(connection, password: str) -> None:
    applied=set()
    with connection.cursor() as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS schema_migrations(filename VARCHAR(255) PRIMARY KEY, applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    connection.commit()
    for extension in sorted((PROJECT_ROOT / "data/schema/extensions").glob("[0-9][0-9]_*.sql")):
        with connection.cursor() as cur:
            cur.execute('SELECT filename FROM schema_migrations WHERE filename=%s',(extension.name,))
            if cur.fetchone():
                print(f'Skipped {extension.name}')
                continue
        if extension.name == "03_chatbot_ro_user.sql":
            with connection.cursor() as cur:
                cur.execute("CREATE USER IF NOT EXISTS 'chatbot_ro'@'localhost' IDENTIFIED BY %s", (password,))
                cur.execute("ALTER USER 'chatbot_ro'@'localhost' IDENTIFIED BY %s", (password,))
                cur.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'chatbot_ro'@'localhost'")
        execute_script(connection, extension)
        with connection.cursor() as cur:
            cur.execute('INSERT INTO schema_migrations(filename) VALUES(%s)',(extension.name,))
        connection.commit()
        applied.add(extension.name)
        print(f"Applied {extension.name}")
    return applied


def verify_counts(connection: mysql.connector.MySQLConnection) -> dict[str, int]:
    queries = {
        "products": ("SELECT COUNT(*) FROM products", ()),
        "product_variants": ("SELECT COUNT(*) FROM product_variants", ()),
        "inventory": ("SELECT COUNT(*) FROM inventory", ()),
        "customers": ("SELECT COUNT(*) FROM users WHERE id > %s AND user_type='customer'", (100,)),
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
    parser.add_argument("--create-if-missing", action="store_true", help="Tạo/seed chỉ khi database chưa tồn tại.")
    parser.add_argument("--extensions-only", action="store_true", help="Áp dụng extension, giữ nguyên dữ liệu.")
    args = parser.parse_args()

    if sum((args.reset, args.create_if_missing, args.extensions_only)) != 1:
        parser.error("Chọn đúng một chế độ: --create-if-missing, --extensions-only, --reset.")

    try:
        config = get_config()
    except (RuntimeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    connection = None
    try:
        connection = connect(config, with_database=False)
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s", (config['database'],))
            exists = bool(cur.fetchone()[0])
        initialize = args.reset or (args.create_if_missing and not exists)
        if initialize:
            execute_script(connection, SCHEMA_FILE, skip_database_drop=not args.reset)
        connection.close()
        connection = connect(config, with_database=True)
        if initialize:
            execute_script(connection, SEED_FILE)
        applied=apply_extensions(connection, str(config['chatbot_ro_password']))
        if initialize or '06_auth_dynamic_rbac.sql' in applied:
            from scripts.seed_demo_passwords import seed
            seed(connection)
        app_password=os.getenv('APP_DB_PASSWORD')
        if not app_password:
            raise RuntimeError('APP_DB_PASSWORD is required')
        if app_password != os.environ['DB_PASSWORD']:
            raise RuntimeError('APP_DB_PASSWORD phải trùng DB_PASSWORD')
        app_user = os.environ['DB_USER']
        if not app_user or app_user == config['user'] or app_user in {'root', 'chatbot_ro'}:
            raise RuntimeError('DB_USER phải là tài khoản ứng dụng riêng, khác tài khoản quản trị và chatbot_ro')
        with connection.cursor() as cur:
            cur.execute("CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s", (app_user, app_password))
            cur.execute("ALTER USER %s@'localhost' IDENTIFIED BY %s", (app_user, app_password))
            cur.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@'localhost'", (app_user,))
            cur.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON honda_chatbot.* TO %s@'localhost'", (app_user,))
        counts = verify_counts(connection)
    except Exception as exc:
        if connection is not None and connection.is_connected():
            connection.close()
        safe_message = str(exc)
        for key in ("password", "chatbot_ro_password"):
            if config.get(key):
                safe_message = safe_message.replace(str(config[key]), "***")
        for key in ('APP_DB_PASSWORD','DEMO_ACCOUNT_PASSWORD'):
            if os.getenv(key):safe_message=safe_message.replace(os.environ[key],'***')
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
