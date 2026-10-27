"""Kiểm chứng cấp quyền và đổi mật khẩu trên MySQL thật, với account tạm riêng."""
import os
from uuid import uuid4

import mysql.connector
import pytest

import init_db
from mysql_accounts import AI_VIEWS, lan_account_host, provision_accounts


@pytest.mark.parametrize('cidr', ['0.0.0.0/0', '127.0.0.0/24', '192.168.0.0/16',
                                  '8.8.8.0/24', '192.168.100.187/24', '::1/128'])
def test_reject_non_lan_or_overbroad_accounts(cidr):
    with pytest.raises(ValueError):
        lan_account_host(cidr)


def test_lan_netmask_is_portable_between_mysql_and_mariadb():
    assert lan_account_host('192.168.100.0/24') == (
        '192.168.100.0/24', '192.168.100.0/255.255.255.0')


@pytest.mark.parametrize('updates', [
    {'APP_DB_PASSWORD': 'different-password'},
    {'DB_USER': 'root'},
    {'DB_USER': 'admin-for-test'},
    {'CHATBOT_RO_USER': 'root'},
    {'CHATBOT_RO_PASSWORD': ''},
    {'ADMIN_DB_USER': ''},
])
def test_invalid_credentials_rejected_before_database_changes(monkeypatch, updates):
    monkeypatch.setattr(init_db, 'load_dotenv', lambda *args: None)
    values = dict(DB_HOST='127.0.0.1', DB_PORT='3306', DB_NAME='honda_chatbot',
                  DB_USER='app-for-test', DB_PASSWORD='app-test-password',
                  APP_DB_PASSWORD='app-test-password', ADMIN_DB_USER='admin-for-test',
                  ADMIN_DB_PASSWORD='', CHATBOT_RO_PASSWORD='readonly-test-password',
                  CHATBOT_RO_USER='chatbot_ro', DEMO_ACCOUNT_PASSWORD='demo-test-password')
    for key, value in (values | updates).items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        init_db.get_config()


def test_account_rotation_reapplies_least_privilege_on_real_mysql():
    config = init_db.get_config()
    admin = init_db.connect(config, True)
    suffix = uuid4().hex[:12]
    app_user, ro_user = 'test_app_' + suffix, 'test_ro_' + suffix
    old_password, new_password = uuid4().hex, uuid4().hex
    connection_config = {key: value for key, value in config.items()
                         if key not in {'user', 'password', 'chatbot_ro_password'}}
    try:
        provision_accounts(admin, app_user, old_password, old_password, ro_user=ro_user)
        # Mô phỏng quyền cấp nhầm trước khi chạy lại script.
        with admin.cursor() as cur:
            cur.execute('GRANT SELECT ON honda_chatbot.users TO %s@%s', (ro_user, 'localhost'))
        provision_accounts(admin, app_user, new_password, new_password, ro_user=ro_user)
        provision_accounts(admin, app_user, new_password, new_password, ro_user=ro_user)
        for user in (app_user, ro_user):
            with pytest.raises(mysql.connector.Error) as rejected:
                mysql.connector.connect(**connection_config, user=user, password=old_password)
            assert rejected.value.errno == 1045
        app = mysql.connector.connect(**connection_config, user=app_user, password=new_password)
        try:
            with app.cursor() as cur:
                cur.execute('UPDATE products SET id=id WHERE 1=0')
            app.rollback()
        finally:
            app.close()
        ro = mysql.connector.connect(**connection_config, user=ro_user, password=new_password)
        try:
            with ro.cursor() as cur:
                for view in AI_VIEWS:
                    cur.execute(f'SELECT * FROM {view} LIMIT 0')
                    cur.fetchall()
                for sql in ('SELECT password_hash FROM users LIMIT 0', 'DELETE FROM products WHERE 1=0'):
                    with pytest.raises(mysql.connector.Error) as forbidden:
                        cur.execute(sql)
                    assert forbidden.value.errno == 1142
                cur.execute('SET @ai_branch = 1, @ai_user = 8')
                cur.execute('SELECT fn_session_branch(), fn_session_user()')
                assert cur.fetchone() == (1, 8)
        finally:
            ro.close()
    finally:
        with admin.cursor() as cur:
            for user in (app_user, ro_user):
                cur.execute('DROP USER IF EXISTS %s@%s', (user, 'localhost'))
        admin.close()


def test_migration_skip_still_updates_chatbot_password_on_real_mysql():
    config = init_db.get_config()
    admin = init_db.connect(config, True)
    password = uuid4().hex
    try:
        # Migration 03 đã chạy; apply_extensions vẫn phải cập nhật credential.
        with admin.cursor() as cur:
            cur.execute('SELECT filename FROM schema_migrations WHERE filename=%s', ('03_chatbot_ro_user.sql',))
            assert cur.fetchone() is not None
        init_db.apply_extensions(admin, password)
        connection_config = {key: value for key, value in config.items()
                             if key not in {'user', 'password', 'chatbot_ro_password'}}
        ro = mysql.connector.connect(**connection_config, user='chatbot_ro', password=password)
        try:
            with ro.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM v_ai_products')
                assert cur.fetchone()[0] > 0
        finally:
            ro.close()
    finally:
        init_db.ensure_account(admin, 'chatbot_ro', config['chatbot_ro_password'], 'localhost')
        admin.close()


def test_ai_extensions_can_be_replayed_twice_on_real_mysql():
    config = init_db.get_config()
    admin = init_db.connect(config, True)
    directory = init_db.PROJECT_ROOT / 'data/schema/extensions'
    before = init_db.verify_counts(admin)
    try:
        for filename in ('02_ai_views.sql', '03_chatbot_ro_user.sql', '04_indexes.sql'):
            for _ in range(2):
                init_db.execute_script(admin, directory / filename)
        assert init_db.verify_counts(admin) == before
    finally:
        # Các extension sau bổ sung cột/scope; trả lại định nghĩa mới nhất cho test tiếp theo.
        for filename in ('05_ai_product_details.sql', '07_own_scope_views.sql', '13_ai_vehicle_releases.sql'):
            init_db.execute_script(admin, directory / filename)
        provision_accounts(admin, os.environ['DB_USER'],
                           os.environ['DB_PASSWORD'], config['chatbot_ro_password'])
        admin.close()
