"""Cấp kết nối MySQL cho backend trong LAN, không thay đổi dữ liệu nghiệp vụ."""
from __future__ import annotations

import argparse
import ipaddress
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from init_db import connect, get_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', required=True, help='Mạng LAN IPv4, ví dụ 192.168.10.0/24')
    args = parser.parse_args()
    network = ipaddress.IPv4Network(args.network, strict=True)
    if not network.is_private or network.prefixlen < 24:
        parser.error('Chỉ cấp cho mạng IPv4 riêng /24 hoặc nhỏ hơn.')
    # Netmask dùng được trên cả MariaDB 10.4 và MySQL 8.
    account_host = f'{network.network_address}/{network.netmask}'
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
        with connection.cursor() as cur:
            for user, password in ((app_user, os.environ['DB_PASSWORD']),
                                   (ro_user, os.environ['CHATBOT_RO_PASSWORD'])):
                cur.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s', (user, account_host, password))
                cur.execute('ALTER USER %s@%s IDENTIFIED BY %s', (user, account_host, password))
                cur.execute('REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@%s', (user, account_host))
            cur.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON honda_chatbot.* TO %s@%s', (app_user, account_host))
            # Tên đối tượng cố định; mọi giá trị cấu hình được bind bằng connector.
            for view in ('v_ai_products', 'v_ai_inventory', 'v_ai_customers', 'v_ai_orders', 'v_ai_product_costs'):
                cur.execute(f'GRANT SELECT ON honda_chatbot.{view} TO %s@%s', (ro_user, account_host))
            for function in ('fn_session_branch', 'fn_session_user'):
                cur.execute(f'GRANT EXECUTE ON FUNCTION honda_chatbot.{function} TO %s@%s', (ro_user, account_host))
        connection.commit()
        print(f'Đã cấp kết nối cho {app_user} và {ro_user} từ {network}; không cấp quyền quản trị.')
    finally:
        connection.close()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Không in thông báo connector có thể chứa giá trị cấu hình bí mật.
        print(f'Cấu hình thất bại ({type(exc).__name__}, mã {getattr(exc, "errno", "không có")}).', file=sys.stderr)
        raise SystemExit(1)
