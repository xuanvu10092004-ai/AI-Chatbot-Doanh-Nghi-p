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
