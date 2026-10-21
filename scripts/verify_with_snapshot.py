# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Chạy reset + pytest rồi khôi phục snapshot, giữ dữ liệu người dùng sau kiểm thử.

Chỉ dành cho máy phát triển; tạm dừng thao tác ghi trên giao diện trong lúc chạy.
Snapshot SQL có dữ liệu riêng tư, nằm trong data/exports được Git bỏ qua.
"""
import hashlib  # So sánh nội dung từng bảng trước và sau quá trình restore.
import os  # Đọc thư mục binary MySQL và truyền mật khẩu qua môi trường subprocess.
import shutil
from pathlib import Path  # Tạo snapshot tạm trong cache bị Git bỏ qua.
import subprocess  # Gọi mysqldump, mysql, init_db và pytest.
import sys  # Dùng cùng Python hiện tại để chạy init_db/pytest.
from uuid import uuid4  # Tạo tên snapshot duy nhất cho lần kiểm tra.

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from init_db import get_config,connect  # Dùng chung cấu hình MySQL và hàm kết nối dự án.


def mysql_binaries(config):
    """Ưu tiên cấu hình/PATH, sau đó lấy basedir của server cục bộ đang dùng."""
    configured = os.getenv('MYSQL_BIN_DIR')
    if configured:
        directory = Path(configured)
    else:
        client = shutil.which('mysql') or shutil.which('mariadb')
        dump = shutil.which('mysqldump') or shutil.which('mariadb-dump')
        if client and dump:
            return Path(dump), Path(client)
        connection = connect(config, True)
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT @@basedir')
                directory = Path(cur.fetchone()[0]) / 'bin'
        finally:
            connection.close()
    suffix = '.exe' if os.name == 'nt' else ''
    dump = directory / ('mysqldump' + suffix)
    client = directory / ('mysql' + suffix)
    if not dump.is_file() or not client.is_file():
        raise RuntimeError('Thiếu mysqldump/mysql; cấu hình MYSQL_BIN_DIR.')
    return dump, client


# Tính số dòng và hash từng bảng để xác nhận restore giữ nguyên dữ liệu.
def fingerprints(config):
    connection=connect(config,True)
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME",(config['database'],))
            names=[r[0] for r in cur.fetchall()]
            result={}
            for name in names:
                # Tên do information_schema trả về, không nhận từ request.
                quoted='`'+name.replace('`','``')+'`'
                cur.execute('SELECT * FROM '+quoted)
                rows=sorted(repr(row) for row in cur.fetchall())
                result[name]=(len(rows),hashlib.sha256('\n'.join(rows).encode()).hexdigest())
            return result
    finally:connection.close()


# Snapshot database cục bộ, chạy reset/test rồi khôi phục và đối chiếu mọi bảng.
def main():
    config=get_config()
    if config['database']!='honda_chatbot' or config['host'] not in {'127.0.0.1','localhost','::1'}:
        raise RuntimeError('Chỉ chạy với database phát triển honda_chatbot trên máy cục bộ.')
    dump,client=mysql_binaries(config)
    folder=ROOT/'data/exports/db-verification';folder.mkdir(parents=True,exist_ok=True)
    snapshot=folder/('before-reset-'+uuid4().hex+'.sql')
    env=dict(os.environ,MYSQL_PWD=str(config['password']))
    args=['--host='+str(config['host']),'--port='+str(config['port']),'--user='+str(config['user']),'--default-character-set=utf8mb4']
    before=fingerprints(config)
    with snapshot.open('wb') as stream:
        subprocess.run([str(dump),*args,'--single-transaction','--routines','--events','--triggers','--hex-blob','--databases','honda_chatbot','--add-drop-database'],stdout=stream,env=env,check=True)
    if snapshot.stat().st_size<1000:raise RuntimeError('Snapshot không hợp lệ; chưa reset.')
    with snapshot.open('rb') as stream:
        stream.seek(max(0,snapshot.stat().st_size-1024))
        if b'Dump completed' not in stream.read():raise RuntimeError('Snapshot chưa hoàn tất; chưa reset.')
    print('Verified snapshot:',snapshot,flush=True)
    # Các test/nghiệp vụ còn xuất Excel. Giữ cả file ngoài database, kể cả file chưa commit.
    assets = (ROOT/'data/source/honda_dataset_khach_hang_san_pham.xlsx',
              ROOT/'data/exports/honda_chatbot_synced.xlsx')
    originals = {path: path.read_bytes() if path.exists() else None for path in assets}
    result=1
    try:
        print('> python init_db.py --reset',flush=True)
        subprocess.run([sys.executable,'-X','utf8','init_db.py','--reset'],cwd=ROOT,check=True)
        # Chuẩn bị workbook từ database vừa seed, không phụ thuộc file của một máy cụ thể.
        subprocess.run([sys.executable,'-X','utf8','-c',
                        'from excel_sync import export_synced_workbook; export_synced_workbook()'],cwd=ROOT,check=True)
        print('> python -m pytest -q',flush=True)
        result=subprocess.run([sys.executable,'-X','utf8','-m','pytest','-q',*sys.argv[1:]],cwd=ROOT).returncode
    finally:
        print('Restoring verified snapshot...',flush=True)
        try:
            with snapshot.open('rb') as stream:
                subprocess.run([str(client),*args,'--binary-mode'],stdin=stream,env=env,check=True)
        finally:
            for path, content in originals.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
        if fingerprints(config)!=before:raise RuntimeError('Dữ liệu sau khôi phục không khớp snapshot; giữ file backup để kiểm tra.')
        print('RESTORE VERIFIED: all table contents match the pre-reset snapshot.',flush=True)
        print('RESTORE VERIFIED: source/export workbook bytes restored.',flush=True)
    return result


if __name__=='__main__':raise SystemExit(main())
