# File này tạo database, nạp schema/dữ liệu và chạy extension SQL theo thứ tự.
from __future__ import annotations

import argparse  # Đọc chế độ reset, tạo mới hoặc áp dụng migration từ CLI.
import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import re  # Tìm và chuẩn hóa mẫu văn bản bằng biểu thức chính quy.
import sys  # Đọc đối số và trạng thái trình thông dịch của công cụ.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
from typing import Iterator  # Khai báo kiểu dữ liệu cho tham số và kết quả.

import mysql.connector  # Dùng driver MySQL và kiểu lỗi/kết nối database.
from dotenv import load_dotenv  # Nạp cấu hình từ file .env.
from mysql_accounts import ensure_account, provision_accounts


PROJECT_ROOT = Path(__file__).resolve().parent
SCHEMA_FILE = PROJECT_ROOT / "data" / "schema" / "honda_chatbot_rbac.sql"
SEED_FILE = PROJECT_ROOT / "data" / "seed" / "honda_import_data.sql"
EXPECTED_COUNTS = {
    "products": 11,
    "product_variants": 31,
    "inventory": 93,
    "customers": 80,
    "customer_profiles": 80,
    "orders": 30,
}


# Nạp .env, kiểm tra các credential bắt buộc và tạo cấu hình MySQL cho init script.
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
        "ADMIN_DB_USER",
        "ADMIN_DB_PASSWORD",
    )
    missing = [name for name in required if os.getenv(name) is None]
    if missing:
        raise RuntimeError(f"Thiếu biến môi trường: {', '.join(missing)}")
    if len(os.environ['DEMO_ACCOUNT_PASSWORD'])<10:
        raise RuntimeError('DEMO_ACCOUNT_PASSWORD must contain at least 10 characters')
    if not os.environ['DB_PASSWORD'] or os.environ['APP_DB_PASSWORD'] != os.environ['DB_PASSWORD']:
        raise RuntimeError('APP_DB_PASSWORD phải trùng DB_PASSWORD và không rỗng')
    if not os.environ['CHATBOT_RO_PASSWORD']:
        raise RuntimeError('CHATBOT_RO_PASSWORD không được rỗng')
    if os.getenv('CHATBOT_RO_USER', 'chatbot_ro') != 'chatbot_ro':
        raise RuntimeError('CHATBOT_RO_USER phải là chatbot_ro')
    if not os.environ['ADMIN_DB_USER'] or not os.environ['DB_USER'] or os.environ['DB_USER'] in {
        'root', 'chatbot_ro', os.environ['ADMIN_DB_USER']
    }:
        raise RuntimeError('DB_USER phải là tài khoản ứng dụng riêng, khác tài khoản quản trị và chatbot_ro')

    database = os.environ["DB_NAME"]
    if database != "honda_chatbot":
        raise RuntimeError("DB_NAME phải là honda_chatbot khi chạy script khởi tạo schema")

    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "user": os.environ['ADMIN_DB_USER'],
        "password": os.environ['ADMIN_DB_PASSWORD'],
        "chatbot_ro_password": os.environ["CHATBOT_RO_PASSWORD"],
        "database": database,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "connection_timeout": 5,
    }


def split_sql_script(script: str) -> Iterator[str]:
    # Tách statement theo dấu chấm phẩy nhưng bỏ qua dấu nằm trong chuỗi/comment.
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
    # Chạy lần lượt statement, tùy chọn bỏ DROP DATABASE và rollback nếu có lỗi.
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


def apply_extensions(connection, password: str) -> set[str]:
    # Áp dụng extension theo số thứ tự và bỏ qua migration đã ghi nhận.
    applied=set()
    with connection.cursor() as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS schema_migrations(filename VARCHAR(255) PRIMARY KEY, applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    connection.commit()
    # Các extension sau cần account này để GRANT. Cập nhật ngay cả khi 03 đã chạy.
    ensure_account(connection, 'chatbot_ro', password, 'localhost')
    for extension in sorted((PROJECT_ROOT / "data/schema/extensions").glob("[0-9][0-9]_*.sql")):
        with connection.cursor() as cur:
            cur.execute('SELECT filename FROM schema_migrations WHERE filename=%s',(extension.name,))
            if cur.fetchone():
                if extension.name == '08_air_blade_125_seed.sql':
                    execute_script(connection, extension)
                print(f'Skipped {extension.name}')
                continue
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
    parser.add_argument('--extension', choices=[p.name for p in sorted((PROJECT_ROOT/'data/schema/extensions').glob('[0-9][0-9]_*.sql'))],
                        help='Chỉ chạy một extension được chỉ định; không seed hoặc đổi account.')
    args = parser.parse_args()

    if sum((args.reset, args.create_if_missing, args.extensions_only, bool(args.extension))) != 1:
        parser.error("Chọn đúng một chế độ: --create-if-missing, --extensions-only, --extension, --reset.")

    try:
        config = get_config()
    except (RuntimeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    connection = None
    try:
        if args.extension:
            connection=connect(config,with_database=True)
            execute_script(connection,PROJECT_ROOT/'data/schema/extensions'/args.extension)
            with connection.cursor() as cur:
                cur.execute('INSERT IGNORE INTO schema_migrations(filename) VALUES(%s)',(args.extension,))
            connection.commit()
            print('Applied '+args.extension+' only; no seed or account changes.')
            return 0
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
        from scripts.backfill_customer_imports import backfill  # Khôi phục lịch sử các dòng khách đã commit.
        recovered=backfill(connection)
        if recovered:print(f'Recovered {recovered} customer import history rows.')
        if initialize or '06_auth_dynamic_rbac.sql' in applied:
            from scripts.seed_demo_passwords import seed  # Đặt lại mật khẩu demo sau khi seed schema.
            seed(connection)
        provision_accounts(connection, os.environ['DB_USER'], os.environ['DB_PASSWORD'],
                           str(config['chatbot_ro_password']))
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
    if initialize and counts != EXPECTED_COUNTS:
        print("Count verification failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
