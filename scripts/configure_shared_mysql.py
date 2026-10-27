# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Cấp kết nối MySQL cho backend trong LAN, không thay đổi dữ liệu nghiệp vụ."""
from __future__ import annotations

import argparse  # Đọc mạng LAN cần cấp quyền từ CLI.
import os  # Đọc user/password DB từ môi trường.
import sys  # Thêm project root vào sys.path và in lỗi ra stderr.
from pathlib import Path  # Tìm root dự án để import init_db.

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from init_db import connect, get_config  # Tái sử dụng cấu hình và kết nối MySQL của ứng dụng.
from mysql_accounts import lan_account_host, provision_accounts


# Tạo user ứng dụng và read-only giới hạn vào mạng LAN đã được chỉ định.
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', required=True, help='Mạng LAN IPv4, ví dụ 192.168.10.0/24')
    args = parser.parse_args()
    try:
        network, account_host = lan_account_host(args.network)
    except ValueError as exc:
        parser.error(str(exc))
    config = get_config()
    if config['host'] not in {'127.0.0.1', 'localhost', '::1'}:
        parser.error('Chạy script trên máy chủ với DB_HOST=127.0.0.1.')
    app_user = os.environ['DB_USER']
    ro_user = os.getenv('CHATBOT_RO_USER', 'chatbot_ro')
    if app_user in {'root', ro_user, config['user']} or ro_user != 'chatbot_ro':
        parser.error('Cần DB_USER riêng và CHATBOT_RO_USER=chatbot_ro.')
    if not os.environ['DB_PASSWORD'] or os.environ['DB_PASSWORD'] != os.environ['APP_DB_PASSWORD']:
        parser.error('DB_PASSWORD và APP_DB_PASSWORD phải trùng nhau và không rỗng.')
    connection = connect(config, with_database=True)
    try:
        provision_accounts(connection, app_user, os.environ['DB_PASSWORD'],
                           os.environ['CHATBOT_RO_PASSWORD'], account_host)
        print(f'Đã cấp kết nối cho {app_user} và {ro_user} từ {network}; không cấp quyền quản trị.')
    finally:
        connection.close()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Không in thông báo connector có thể chứa giá trị cấu hình bí mật.
        print(f'Cấu hình thất bại ({type(exc).__name__}, mã {getattr(exc, "errno", "không có")}).', file=sys.stderr)
        raise SystemExit(1)
