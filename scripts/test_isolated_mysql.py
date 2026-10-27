"""Copy the configured DB into a private MariaDB process; never reset the source.

Windows MariaDB distribution with mysql_install_db.exe is required. Private files
stay under ignored data/exports for inspection. No credentials are printed.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from init_db import get_config, connect, execute_script
from mysql_accounts import provision_accounts
from scripts.verify_with_snapshot import mysql_binaries, fingerprints


def main():
    config = get_config()
    dump, client = mysql_binaries(config)
    server = client.parent / 'mysqld.exe'
    installer = client.parent / 'mysql_install_db.exe'
    if not server.is_file() or not installer.is_file():
        raise RuntimeError('Cần MariaDB Windows với mysqld/mysql_install_db để tạo server riêng.')
    folder = ROOT / 'data/exports' / ('isolated-mysql-' + uuid4().hex)
    folder.mkdir(parents=True)
    datadir = folder / 'mysql-data'
    before = fingerprints(config)
    snapshot = folder / 'source.sql'
    env = dict(os.environ, MYSQL_PWD=str(config['password']))
    args = ['--host=' + str(config['host']), '--port=' + str(config['port']),
            '--user=' + str(config['user']), '--default-character-set=utf8mb4']
    with snapshot.open('wb') as stream:
        subprocess.run([str(dump), *args, '--single-transaction', '--routines',
                        '--events', '--triggers', '--hex-blob', '--databases',
                        str(config['database'])], stdout=stream, env=env, check=True)
    if snapshot.stat().st_size < 1000:
        raise RuntimeError('Snapshot trống; chưa khởi chạy test.')
    subprocess.run([str(installer), '--datadir=' + str(datadir)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    log = (folder / 'server.log').open('wb')
    process = subprocess.Popen([str(server), '--no-defaults', '--datadir=' + str(datadir),
                                '--basedir=' + str(client.parent.parent), '--port=' + str(port),
                                '--bind-address=127.0.0.1', '--console'], stdout=log, stderr=log,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    test_config = {**config, 'host': '127.0.0.1', 'port': port, 'user': 'root', 'password': ''}
    try:
        for _ in range(100):
            try:
                connection = connect(test_config, False)
                connection.close()
                break
            except Exception:
                if process.poll() is not None:
                    raise RuntimeError('Server test chưa chạy; xem ' + str(folder / 'server.log'))
                time.sleep(.1)
        else:
            raise RuntimeError('Timeout khởi động server test.')
        private_env = dict(os.environ, DB_HOST='127.0.0.1', DB_PORT=str(port),
                           ADMIN_DB_USER='root', ADMIN_DB_PASSWORD='', MYSQL_PWD='',
                           GROQ_API_KEY='', APP_ENV='dev')
        with snapshot.open('rb') as stream:
            subprocess.run([str(client), '--host=127.0.0.1', '--port=' + str(port),
                            '--user=root', '--binary-mode'], stdin=stream, env=private_env, check=True)
        connection = connect(test_config, True)
        try:
            provision_accounts(connection, os.environ['DB_USER'], os.environ['DB_PASSWORD'],
                               config['chatbot_ro_password'])
            for extension in sorted((ROOT / 'data/schema/extensions').glob('1[6-9]_*.sql')):
                execute_script(connection, extension)
        finally:
            connection.close()
        print('ISOLATED MariaDB port=' + str(port) + '; source copied, never reset.', flush=True)
        # Only additive extensions for this feature, on the private copy.
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q',
                                 *sys.argv[1:]], cwd=ROOT, env=private_env)
        print('pytest exit code:', result.returncode, flush=True)
        return result.returncode
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()
        print('Source table contents unchanged:', fingerprints(config) == before, flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
