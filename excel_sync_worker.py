"""Durable MySQL outbox -> one atomic workbook, independent of Flask/browser."""
import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
import time

from db import cursor, get_connection, transaction_active


def sync_status():
    with cursor() as cur:
        cur.execute('SELECT * FROM excel_sync_state WHERE id=1');state=cur.fetchone()
        cur.execute('SELECT COUNT(*) AS n FROM excel_sync_changes WHERE processed_at IS NULL');pending=cur.fetchone()['n']
    if not state:raise RuntimeError('Cần migration excel_sync_outbox.')
    status='failed' if state['status']=='failed' else 'running' if state['status']=='running' else 'pending' if pending else 'completed' if state['last_success_at'] else 'pending'
    result={'status':status,'pending':pending,'last_success_at':state['last_success_at'],
            'last_worker_at':state['last_worker_at'],'error':state['last_error'],
            'attempts':state['attempts'],'next_retry_at':state['next_retry_at'],
            'watermark':state['last_change_id'],'path':state['output_path']}
    return {key:value.isoformat() if isinstance(value,datetime) else value for key,value in result.items()}


def process_sync(force=False,path=None):
    from excel_sync import SYNCED_WORKBOOK,SOURCE_WORKBOOK,_rows,_write_workbook
    if transaction_active():
        return {'status':'pending','error':'Chỉ xuất sau khi transaction dữ liệu đã commit.'}
    target=Path(path) if path is not None else SYNCED_WORKBOOK
    if target.resolve()==SOURCE_WORKBOOK.resolve():raise ValueError('Không ghi đè workbook nguồn.')
    official=target.resolve()==SYNCED_WORKBOOK.resolve()
    connection=get_connection()
    locked=False
    cur=connection.cursor(dictionary=True)
    try:
        # Connection-scoped lock works across processes and is released on crash.
        lock_name='excel_sync:'+str(connection.database)
        cur.execute('SELECT GET_LOCK(%s,0) AS locked',(lock_name,));locked=cur.fetchone()['locked']==1
        connection.commit()
        if not locked:return {'status':'busy','error':'Worker khác đang đồng bộ Excel.'}
        cur.execute('SELECT *,next_retry_at>NOW() AS wait_retry FROM excel_sync_state WHERE id=1');state=cur.fetchone()
        if not force and state['wait_retry']:return {'status':'pending','next_retry_at':state['next_retry_at']}
        if official:
            cur.execute("UPDATE excel_sync_state SET last_worker_at=NOW() WHERE id=1")
        connection.commit()
        connection.start_transaction(consistent_snapshot=True,isolation_level='REPEATABLE READ')
        cur.execute('SELECT id FROM excel_sync_changes WHERE processed_at IS NULL ORDER BY id LIMIT 10000')
        ids=[row['id'] for row in cur.fetchall()]
        if not ids and not force:
            connection.commit()
            return {'status':'idle'}
        # All sheets and event IDs belong to the same committed DB snapshot.
        data=_rows(cur)
        connection.commit()
        if official:
            cur.execute("UPDATE excel_sync_state SET status='running',last_error=NULL WHERE id=1")
            connection.commit()
        _write_workbook(data,target)
        if official:
            # Never ACK by MAX(id): lower IDs may commit *after* our snapshot.
            if ids:
                cur.execute('UPDATE excel_sync_changes SET processed_at=NOW(6) WHERE id IN ('+
                            ','.join('%s' for _ in ids)+')',tuple(ids))
            cur.execute("UPDATE excel_sync_state SET status='success',last_success_at=NOW(),last_error=NULL,attempts=0,next_retry_at=NULL,last_change_id=GREATEST(last_change_id,%s),output_path=%s WHERE id=1",
                        (max(ids,default=0),str(target.resolve())))
            connection.commit()
        return {'status':'completed','path':str(target),'events':len(ids)}
    except Exception as error:
        connection.rollback()
        # Persist failure without consuming the events; retry can survive restart.
        message='Không thay được file Excel; hãy đóng file rồi chờ worker thử lại.' if isinstance(error,PermissionError) else 'Lỗi xuất Excel: '+type(error).__name__
        if official and locked:
            try:
                cur.execute('SELECT attempts FROM excel_sync_state WHERE id=1');attempts=cur.fetchone()['attempts']+1
                delay=min(300,2**min(attempts,8))
                cur.execute("UPDATE excel_sync_state SET status='failed',attempts=%s,last_error=%s,next_retry_at=DATE_ADD(NOW(),INTERVAL %s SECOND) WHERE id=1",(attempts,message,delay))
                connection.commit()
            except Exception:
                connection.rollback()
                logging.exception('Không ghi được trạng thái worker; event vẫn chưa ACK')
        return {'status':'failed','error':message}
    finally:
        try:
            connection.rollback()
            if locked:
                cur.execute('SELECT RELEASE_LOCK(%s)',(lock_name,));cur.fetchone()
        finally:
            cur.close();connection.close()


def main():
    parser=argparse.ArgumentParser(description='Đồng bộ MySQL dùng chung sang Excel chính thức')
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--interval',type=float,default=2)
    args=parser.parse_args()
    if args.interval<.1:parser.error('interval phải >=0.1 giây')
    if args.force and not args.once:parser.error('--force chỉ dùng cùng --once; worker thường chỉ xử lý event chờ.')
    log=Path(__file__).resolve().parent/'data/exports/excel_sync_worker.log'
    log.parent.mkdir(parents=True,exist_ok=True)
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(log,maxBytes=2_000_000,backupCount=3,encoding='utf-8')])
    while True:
        try:
            result=process_sync(force=args.force)
            if result['status'] not in {'idle','busy'}:logging.info('%s',json.dumps(result,default=str,ensure_ascii=False))
        except Exception as error:
            result={'status':'failed','error':type(error).__name__}
            logging.error('Chưa kết nối được MySQL: %s',type(error).__name__)
        if args.once:
            print(json.dumps(result,default=str,ensure_ascii=False))
            return 1 if result['status']=='failed' else 0
        time.sleep(args.interval)


if __name__=='__main__':raise SystemExit(main())
