"""Chỉ đặt mật khẩu demo khi khởi tạo mới hoặc chạy trực tiếp có chủ đích."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werkzeug.security import generate_password_hash


def seed(connection):
    password=os.getenv('DEMO_ACCOUNT_PASSWORD')
    if not password or len(password)<10:
        raise RuntimeError('DEMO_ACCOUNT_PASSWORD must contain at least 10 characters')
    with connection.cursor() as cur:
        for user_id in range(1,10):
            cur.execute('UPDATE users SET password_hash=%s, password_updated_at=NOW(), failed_login_count=0, locked_until=NULL WHERE id=%s', (generate_password_hash(password),user_id))
    connection.commit()


if __name__=='__main__':
    from init_db import get_config,connect
    connection=connect(get_config(),True)
    try:seed(connection)
    finally:connection.close()
    print('Demo passwords initialized (not displayed).')
