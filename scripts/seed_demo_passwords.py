# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Chỉ đặt mật khẩu demo khi khởi tạo mới hoặc chạy trực tiếp có chủ đích."""
import os  # Đọc mật khẩu demo từ môi trường, không in ra terminal.
import sys  # Thêm root project vào sys.path và trả mã thoát.
from pathlib import Path  # Xác định root project để import init_db.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werkzeug.security import generate_password_hash  # Băm mật khẩu trước khi ghi vào users.


# Đặt lại mật khẩu demo và trạng thái khóa cho các user seed từ 1 đến 9.
def seed(connection):
    password=os.getenv('DEMO_ACCOUNT_PASSWORD')
    if not password or len(password)<10:
        raise RuntimeError('DEMO_ACCOUNT_PASSWORD must contain at least 10 characters')
    with connection.cursor() as cur:
        for user_id in range(1,10):
            cur.execute('UPDATE users SET password_hash=%s, password_updated_at=NOW(), failed_login_count=0, locked_until=NULL WHERE id=%s', (generate_password_hash(password),user_id))
    connection.commit()


if __name__=='__main__':
    from init_db import get_config,connect  # Dùng cấu hình, script SQL và kiểm tra schema khởi tạo.
    connection=connect(get_config(),True)
    try:seed(connection)
    finally:connection.close()
    print('Demo passwords initialized (not displayed).')
