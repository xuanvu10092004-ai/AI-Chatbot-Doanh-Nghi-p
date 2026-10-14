"""Kiểm tra MySQL hiện hành, không tạo hoặc đọc database SQLite cũ.

Chạy python check_db.py để xem số bản ghi và nơi lưu tài khoản.
Không in email, mật khẩu, hash hoặc thông tin bí mật từ .env.
"""
from db import get_connection
from init_db import verify_counts


def check_database():
    """Đọc cấu hình .env và chạy các truy vấn thống kê cố định, chỉ đọc."""
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT DATABASE(), VERSION()')
            database, version = cur.fetchone()
            print(f'Cơ sở dữ liệu: {database}; máy chủ: {version}')
        for table, count in verify_counts(connection).items():
            print(f'{table}: {count}')
        # Tài khoản MySQL khác với tài khoản đăng nhập ứng dụng.
        # Email và hash nằm trong users, quyền nằm trong các bảng RBAC.
        with connection.cursor() as cur:
            cur.execute('SELECT COUNT(*), SUM(is_active=TRUE) FROM users')
            total, active = cur.fetchone()
            print(f'Tài khoản trong users: {total}; đang hoạt động: {active}')
        print('Quản lý tài khoản: /admin/users (quyền user:manage).')
        print('Vai trò/quyền: roles, user_roles, permissions, role_permissions.')
    finally:
        connection.close()


if __name__ == '__main__':
    check_database()
