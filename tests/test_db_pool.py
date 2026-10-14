"""MySQL thật: request đồng thời chờ kết nối bận được trả lại."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError

import pytest

from db import get_connection


def test_busy_pool_waits_for_returned_connection():
    held = [get_connection() for _ in range(5)]
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(get_connection)
            with pytest.raises(TimeoutError):
                pending.result(timeout=0.1)
            held.pop().close()
            connection = pending.result(timeout=2)
            try:
                with connection.cursor() as cur:
                    cur.execute('SELECT 1')
                    assert cur.fetchone() == (1,)
            finally:
                connection.close()
    finally:
        for connection in held:
            connection.close()
