"""Cấp lại quyền MySQL cục bộ/LAN từ cùng một cấu hình, không ghi mật khẩu ra SQL file."""
from __future__ import annotations

import ipaddress


AI_VIEWS = ('v_ai_products', 'v_ai_inventory', 'v_ai_customers', 'v_ai_orders', 'v_ai_product_costs')
SCOPE_FUNCTIONS = ('fn_session_branch', 'fn_session_user')
PRIVATE_NETWORKS = tuple(ipaddress.IPv4Network(cidr) for cidr in
                         ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


def lan_account_host(cidr: str) -> tuple[str, str]:
    """Chỉ nhận mạng RFC1918 /24 hoặc nhỏ hơn, dùng netmask tương thích MySQL/MariaDB."""
    network = ipaddress.IPv4Network(cidr, strict=True)
    if network.prefixlen < 24 or not any(network.subnet_of(private) for private in PRIVATE_NETWORKS):
        raise ValueError('Chỉ cấp cho mạng LAN IPv4 riêng /24 hoặc nhỏ hơn.')
    return str(network), f'{network.network_address}/{network.netmask}'


def ensure_account(connection, user: str, password: str, host: str) -> None:
    with connection.cursor() as cur:
        cur.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s', (user, host, password))
        cur.execute('ALTER USER %s@%s IDENTIFIED BY %s', (user, host, password))


def provision_accounts(connection, app_user: str, app_password: str,
                       ro_password: str, host: str = 'localhost',
                       ro_user: str = 'chatbot_ro') -> None:
    """Chạy lại luôn cập nhật mật khẩu và quyền, kể cả khi migration 03 đã được ghi nhận."""
    if not app_user or app_user in {'root', ro_user} or not app_password or not ro_password:
        raise ValueError('Cần tài khoản ứng dụng riêng và mật khẩu không rỗng.')
    for user, password in ((app_user, app_password), (ro_user, ro_password)):
        ensure_account(connection, user, password, host)
        with connection.cursor() as cur:
            cur.execute('REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@%s', (user, host))
    with connection.cursor() as cur:
        cur.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON honda_chatbot.* TO %s@%s', (app_user, host))
        # Chỉ tên đối tượng hằng số được đưa vào SQL; user, host và mật khẩu đều bind.
        for view in AI_VIEWS:
            cur.execute(f'GRANT SELECT ON honda_chatbot.{view} TO %s@%s', (ro_user, host))
        for function in SCOPE_FUNCTIONS:
            cur.execute(f'GRANT EXECUTE ON FUNCTION honda_chatbot.{function} TO %s@%s', (ro_user, host))
    connection.commit()
