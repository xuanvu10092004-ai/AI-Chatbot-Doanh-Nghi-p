import ctypes
import os
from pathlib import Path
import subprocess
import sys

from openpyxl import load_workbook
import pytest

from db import cursor,get_connection,transaction
from excel_sync import SOURCE_WORKBOOK
from excel_sync_worker import process_sync,sync_status


@pytest.fixture
def output(tmp_path,monkeypatch):
    path=tmp_path/'official.xlsx'
    monkeypatch.setattr('excel_sync.SYNCED_WORKBOOK',path)
    assert process_sync(force=True)['status']=='completed'
    return path


def exported_name(output,email):
    book=load_workbook(output,read_only=True,data_only=True)
    try:return next(row[1] for row in book['Khach_hang'].iter_rows(min_row=2,values_only=True) if row[6]==email)
    finally:book.close()


def test_direct_sql_is_detected_coalesced_and_source_untouched(output,monkeypatch):
    import excel_sync
    source=SOURCE_WORKBOOK.read_bytes()
    calls=[];write=excel_sync._write_workbook
    def counted(*args):calls.append(True);return write(*args)
    monkeypatch.setattr(excel_sync,'_write_workbook',counted)
    with cursor() as cur:
        cur.execute('SELECT id,email,full_name FROM users WHERE id=101');record=cur.fetchone()
    try:
        with cursor() as cur:
            cur.execute('UPDATE users SET full_name=%s WHERE id=101',('Khách SQL trực tiếp',))
            cur.execute('UPDATE inventory SET quantity=quantity+1 WHERE variant_id=14')
            cur.execute('UPDATE inventory SET quantity=quantity-1 WHERE variant_id=14')
        assert sync_status()['pending']>=3
        assert process_sync()['status']=='completed'
        assert calls==[True] and exported_name(output,record['email'])=='Khách SQL trực tiếp'
        assert sync_status()['pending']==0 and SOURCE_WORKBOOK.read_bytes()==source
    finally:
        with cursor() as cur:cur.execute('UPDATE users SET full_name=%s WHERE id=101',(record['full_name'],))


def test_rollback_does_not_enqueue_or_change_workbook(output):
    before=output.read_bytes();pending=sync_status()['pending']
    with pytest.raises(RuntimeError):
        with transaction():
            with cursor() as cur:cur.execute("UPDATE users SET full_name='Không commit' WHERE id=101")
            assert process_sync(force=True)['status']=='pending'
            raise RuntimeError('rollback')
    assert sync_status()['pending']==pending
    assert process_sync()['status']=='idle' and output.read_bytes()==before


def test_failed_replace_retains_export_and_events_for_restart(output,monkeypatch):
    from excel_sync import _write_workbook
    before=output.read_bytes()
    with cursor() as cur:cur.execute('UPDATE inventory SET quantity=quantity WHERE variant_id=14')
    pending=sync_status()['pending']
    def locked(*args):raise PermissionError('locked')
    monkeypatch.setattr('excel_sync._write_workbook',locked)
    assert process_sync()['status']=='failed'
    status=sync_status()
    assert status['pending']==pending and status['attempts']>=1 and status['next_retry_at']
    assert output.read_bytes()==before
    monkeypatch.setattr('excel_sync._write_workbook',_write_workbook)
    # A new worker invocation resumes from DB state, not in-memory progress.
    assert process_sync(force=True)['status']=='completed'
    assert sync_status()['pending']==0 and sync_status()['error'] is None


def test_late_commit_lower_event_id_is_not_skipped(output):
    connection=get_connection();cur=connection.cursor(dictionary=True)
    with cursor() as q:
        q.execute('SELECT email,full_name FROM users WHERE id=101');record=q.fetchone()
    try:
        cur.execute('UPDATE users SET full_name=%s WHERE id=101',('Commit muộn',))
        with cursor() as q:q.execute('UPDATE inventory SET quantity=quantity WHERE branch_id=1 AND variant_id=15')
        assert process_sync()['status']=='completed'
        assert exported_name(output,record['email'])==record['full_name']
        connection.commit()
        assert sync_status()['pending']>0
        assert process_sync()['status']=='completed'
        assert exported_name(output,record['email'])=='Commit muộn'
    finally:
        connection.rollback();cur.close();connection.close()
        with cursor() as q:q.execute('UPDATE users SET full_name=%s WHERE id=101',(record['full_name'],))


def test_another_process_cannot_export_while_lock_held(output):
    connection=get_connection();cur=connection.cursor()
    key='excel_sync:'+connection.database
    try:
        cur.execute('SELECT GET_LOCK(%s,0)',(key,));assert cur.fetchone()[0]==1
        child=subprocess.run([sys.executable,'-X','utf8','excel_sync_worker.py','--once','--force'],capture_output=True,text=True,encoding='utf-8',timeout=20)
        assert child.returncode==0 and 'busy' in child.stdout,child.stderr
    finally:
        cur.execute('SELECT RELEASE_LOCK(%s)',(key,));cur.fetchone();cur.close();connection.close()


@pytest.mark.skipif(os.name!='nt',reason='Khóa file bằng Windows CreateFileW')
def test_real_windows_excel_file_lock_and_recovery(output):
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(output),0x80000000,1,None,3,0,None)
    assert handle not in (None,ctypes.c_void_p(-1).value),ctypes.get_last_error()
    try:
        assert process_sync(force=True)['status']=='failed'
        assert sync_status()['status']=='failed'
    finally:kernel.CloseHandle(handle)
    assert process_sync(force=True)['status']=='completed'


def test_crash_after_replace_before_ack_is_recoverable(output,monkeypatch):
    import excel_sync
    write=excel_sync._write_workbook
    with cursor() as cur:cur.execute('UPDATE inventory SET quantity=quantity WHERE variant_id=14')
    pending=sync_status()['pending']
    def crash(*args):
        write(*args)
        raise SystemExit('mô phỏng worker bị dừng')
    monkeypatch.setattr(excel_sync,'_write_workbook',crash)
    with pytest.raises(SystemExit):process_sync()
    assert sync_status()['pending']==pending
    monkeypatch.setattr(excel_sync,'_write_workbook',write)
    assert process_sync()['status']=='completed' and sync_status()['pending']==0


def test_many_committed_writes_have_one_consistent_final_export(output,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import excel_sync
    with cursor() as cur:
        cur.execute('SELECT branch_id,variant_id,quantity FROM inventory WHERE variant_id<=8');before=cur.fetchall()
    def update(index):
        with cursor() as cur:cur.execute('UPDATE inventory SET quantity=quantity+1 WHERE variant_id=%s',(index%8+1,))
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(update,range(24)))
        calls=[];write=excel_sync._write_workbook
        monkeypatch.setattr(excel_sync,'_write_workbook',lambda *a:(calls.append(True),write(*a))[1])
        assert process_sync()['status']=='completed' and calls==[True]
        book=load_workbook(output,read_only=True,data_only=True)
        try:
            products={row[0]:row[16] for row in book['San_pham'].iter_rows(min_row=2,values_only=True)}
            inventory={row[0]:row[6] for row in book['Ton_kho'].iter_rows(min_row=2,values_only=True)}
            assert products==inventory
            with cursor() as cur:
                cur.execute('SELECT variant_id,SUM(quantity) AS n FROM inventory GROUP BY variant_id')
                assert inventory=={f"SP{r['variant_id']:03d}":r['n'] for r in cur.fetchall()}
            assert sum(inventory[f"SP{r['variant_id']:03d}"] for r in before if r['branch_id']==1)==sum(r['quantity'] for r in before)+len(before)*3
        finally:book.close()
    finally:
        with cursor() as cur:
            for row in before:cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s',(row['quantity'],row['branch_id'],row['variant_id']))


def test_worker_subprocess_exports_without_flask_or_browser():
    with cursor() as cur:cur.execute('UPDATE inventory SET quantity=quantity WHERE variant_id=14')
    child=subprocess.run([sys.executable,'-X','utf8','excel_sync_worker.py','--once','--force'],capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert child.returncode==0 and 'completed' in child.stdout,child.stderr
    assert sync_status()['pending']==0
