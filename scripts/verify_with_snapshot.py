# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Chạy reset + pytest rồi khôi phục snapshot, giữ dữ liệu người dùng sau kiểm thử.

Chỉ dành cho máy phát triển; tạm dừng thao tác ghi trên giao diện trong lúc chạy.
Snapshot SQL có dữ liệu riêng tư, nằm trong .pytest_cache được Git bỏ qua.
"""
import hashlib  # So sánh nội dung từng bảng trước và sau quá trình restore.
import os  # Đọc thư mục binary MySQL và truyền mật khẩu qua môi trường subprocess.
from pathlib import Path  # Tạo snapshot tạm trong cache bị Git bỏ qua.
import subprocess  # Gọi mysqldump, mysql, init_db và pytest.
import sys  # Dùng cùng Python hiện tại để chạy init_db/pytest.
from uuid import uuid4  # Tạo tên snapshot duy nhất cho lần kiểm tra.

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from init_db import get_config,connect  # Dùng chung cấu hình MySQL và hàm kết nối dự án.


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
    binaries=Path(os.environ.get('MYSQL_BIN_DIR','D:/general software/xampp/mysql/bin'))
    dump=binaries/'mysqldump.exe';client=binaries/'mysql.exe'
    if not dump.is_file() or not client.is_file():raise RuntimeError('Thiếu mysqldump/mysql; cấu hình MYSQL_BIN_DIR.')
    folder=ROOT/'.pytest_cache';folder.mkdir(exist_ok=True)
    snapshot=folder/('before-reset-'+uuid4().hex+'.sql')
    env=dict(os.environ,MYSQL_PWD=str(config['password']))
    args=['--host='+str(config['host']),'--port='+str(config['port']),'--user='+str(config['user']),'--default-character-set=utf8mb4']
    before=fingerprints(config)
    subprocess.run([str(dump),*args,'--single-transaction','--routines','--events','--triggers','--hex-blob','--databases','honda_chatbot','--add-drop-database','--result-file='+str(snapshot)],env=env,check=True)
    if snapshot.stat().st_size<1000:raise RuntimeError('Snapshot không hợp lệ; chưa reset.')
    with snapshot.open('rb') as stream:
        stream.seek(max(0,snapshot.stat().st_size-1024))
        if b'Dump completed' not in stream.read():raise RuntimeError('Snapshot chưa hoàn tất; chưa reset.')
    print('Verified snapshot:',snapshot,flush=True)
    result=1
    try:
        print('> python init_db.py --reset',flush=True)
        subprocess.run([sys.executable,'-X','utf8','init_db.py','--reset'],cwd=ROOT,check=True)
        print('> python -m pytest -q',flush=True)
        result=subprocess.run([sys.executable,'-X','utf8','-m','pytest','-q',*sys.argv[1:]],cwd=ROOT).returncode
    finally:
        print('Restoring verified snapshot...',flush=True)
        with snapshot.open('rb') as stream:
            subprocess.run([str(client),*args,'--binary-mode'],stdin=stream,env=env,check=True)
        if fingerprints(config)!=before:raise RuntimeError('Dữ liệu sau khôi phục không khớp snapshot; giữ file backup để kiểm tra.')
        print('RESTORE VERIFIED: all table contents match the pre-reset snapshot.',flush=True)
    return result


if __name__=='__main__':raise SystemExit(main())
