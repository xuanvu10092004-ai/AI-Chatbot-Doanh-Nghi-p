"""Kiểm tra máy đích, migration và quyền chatbot từ một máy backend trong LAN."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mysql.connector
from db import _base_config, _required
from mysql_accounts import AI_VIEWS, SCOPE_FUNCTIONS

ROOT = Path(__file__).resolve().parents[1]


def check(host: str | None = None) -> None:
    config = _base_config()
    if host:
        config['host'] = host
    print(f"Máy đích: {config['host']}:{config['port']}/{config['database']}")
    connection = mysql.connector.connect(**config, user=_required('DB_USER'), password=_required('DB_PASSWORD'))
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT @@hostname, @@port, DATABASE(), CURRENT_USER()')
            server, port, database, account = cur.fetchone()
            print(f'Máy chủ MySQL: {server}:{port}; CSDL: {database}; tài khoản: {account}')
            cur.execute('SELECT filename FROM schema_migrations')
            applied = {row[0] for row in cur.fetchall()}
            expected = {path.name for path in (ROOT / 'data/schema/extensions').glob('[0-9][0-9]_*.sql')}
            missing = sorted(expected - applied)
            if missing:
                raise RuntimeError('Thiếu migration: ' + ', '.join(missing) +
                                   '. Chạy init_db.py --extensions-only trên máy chủ.')
            print(f'Migration: đủ {len(expected)} file.')
            cur.execute('SELECT COUNT(*) FROM orders')
            print(f'Số đơn hàng: {cur.fetchone()[0]}')
    finally:
        connection.close()
    connection = mysql.connector.connect(**config, user=os.getenv('CHATBOT_RO_USER', 'chatbot_ro'),
                                         password=_required('CHATBOT_RO_PASSWORD'))
    try:
        with connection.cursor() as cur:
            cur.execute('SET @ai_branch = NULL, @ai_user = NULL')
            for view in AI_VIEWS:
                cur.execute(f'SELECT * FROM {view} LIMIT 0')
                cur.fetchall()
            for function in SCOPE_FUNCTIONS:
                cur.execute(f'SELECT {function}()')
                cur.fetchone()
            # Xác nhận view đọc được nhưng bảng gốc không được phép đọc.
            try:
                cur.execute('SELECT password_hash FROM users LIMIT 0')
                cur.fetchall()
            except mysql.connector.Error as exc:
                if exc.errno != 1142:
                    raise
            else:
                raise RuntimeError('Tài khoản chatbot đang có quyền đọc bảng gốc. Cần cấp lại quyền trên máy chủ.')
            cur.execute('SELECT COUNT(*) FROM v_ai_inventory')
            print(f'Chatbot: đọc được {len(AI_VIEWS)} view và hàm scope; {cur.fetchone()[0]} dòng tồn kho; bảng gốc bị chặn.')
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', help='Kiểm tra IP máy chủ, không sửa .env.')
    args = parser.parse_args()
    try:
        check(args.host)
    except mysql.connector.Error as exc:
        hints = {
            1045: 'Sai tài khoản/mật khẩu hoặc chưa cấp quyền cho IP máy backend. Kiểm tra .env và chạy configure_shared_mysql.py trên máy chủ.',
            1130: 'IP máy backend chưa được cấp quyền kết nối. Chạy configure_shared_mysql.py trên máy chủ.',
            2003: 'Không tới được MySQL. Kiểm tra IP LAN, cổng 3306, dịch vụ MySQL và firewall.',
            2005: 'Không phân giải được tên máy chủ. Kiểm tra DB_HOST.',
            1049: 'Chưa có database. Khởi tạo trên máy chủ bằng --create-if-missing.',
            1146: 'Thiếu bảng hoặc migration. Chạy --extensions-only trên máy chủ.',
            1356: 'View hoặc DEFINER không hợp lệ. Cần kiểm tra bản sao lưu và quyền trên máy chủ.',
        }
        print(f"Kiểm tra thất bại (mã {exc.errno}). " + hints.get(exc.errno, 'Kiểm tra quyền và migration trên máy chủ.'), file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print('Kết nối ứng dụng và chatbot đều đạt. Các máy cần cùng máy đích và máy chủ MySQL ở trên.')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
