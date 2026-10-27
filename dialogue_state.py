"""Serialize turns for one owned server-side conversation, across workers."""
from contextlib import contextmanager
import json

from db import cursor, transaction


@contextmanager
def dialogue_turn(session_id, user_id):
    with transaction():
        with cursor() as cur:
            cur.execute('SELECT id FROM chat_sessions WHERE id=%s AND user_id <=> %s FOR UPDATE',
                        (session_id, user_id))
            if not cur.fetchone():
                raise ValueError('Conversation owner mismatch')
            cur.execute('SELECT payload,updated_at<NOW()-INTERVAL 30 MINUTE AS expired '
                        'FROM chat_dialogue_state WHERE session_id=%s AND user_id <=> %s',
                        (session_id, user_id))
            row = cur.fetchone()
        state = json.loads(row['payload']) if row and not row['expired'] else {}
        yield state
        with cursor() as cur:
            cur.execute('INSERT INTO chat_dialogue_state(session_id,user_id,payload) VALUES(%s,%s,%s) '
                        'ON DUPLICATE KEY UPDATE payload=VALUES(payload),version=version+1',
                        (session_id, user_id, json.dumps(state, ensure_ascii=False, default=str)))


def remember_evidence(session_id, user_id, rows):
    if not rows:
        return
    with dialogue_turn(session_id,user_id) as state:
        models={r['model_name'] for r in rows if r.get('model_name')}
        if len(models)==1:
            state['product_context']=next(iter(models))
        for source,target in (('customer_id','customer_id'),('order_id','order_id')):
            ids={r[source] for r in rows if r.get(source)}
            if len(ids)==1:state.setdefault('entities',{})[target]=next(iter(ids))
