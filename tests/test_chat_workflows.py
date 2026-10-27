import pytest

from db import cursor
from operations_routes import OperationRejected
from test_chat_tools_imports import chat, confirm, tool_cleanup, no_live_model


def stock():
    with cursor() as cur:
        cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14')
        return cur.fetchone()['quantity']


def test_read_then_write_waits_for_confirmation(auth_client, tool_cleanup):
    auth_client.login(2)
    before = stock()
    reply = chat(auth_client, 'Xem tổng quan tồn kho rồi nhập hàng: Nhà cung cấp: Kho quy trình; Mã SP: SP014; Số lượng: 2')
    assert reply['steps'][0]['rows']
    assert 'action_draft' in reply and stock() == before
    result = confirm(auth_client, reply)
    assert result['result']['received_quantity'] == 2 and stock() == before + 2
    assert confirm(auth_client, reply)['result'] == result['result']


def test_two_writes_need_two_distinct_confirmations(auth_client, tool_cleanup):
    auth_client.login(2)
    before = stock()
    command = 'Nhập hàng: Nhà cung cấp: Kho quy trình; Mã SP: SP014; Số lượng: 2'
    first = chat(auth_client, command + ' rồi ' + command)
    second = confirm(auth_client, first)
    assert stock() == before + 2
    assert second['action_draft']['id'] != first['action_draft']['id']
    assert confirm(auth_client, second)['result']['received_quantity'] == 2
    assert stock() == before + 4


def test_whole_sequence_authorized_before_first_read(auth_client, tool_cleanup, monkeypatch):
    auth_client.login(3)
    def forbidden(*a, **kw):
        pytest.fail('Không đọc khi một bước trong quy trình ngoài quyền')
    monkeypatch.setattr('dashboard_service.widget_data', forbidden)
    result = chat(auth_client, 'Xem tổng quan tồn kho rồi nhập hàng: Mã SP: SP014; Số lượng: 2')
    assert result['access_denied'] and 'action_draft' not in result


def test_condition_rechecked_at_confirmation(auth_client, tool_cleanup):
    auth_client.login(2)
    before = stock()
    limit = before + 1
    reply = chat(auth_client, f'Tồn kho SP014 tại NT01, nếu dưới {limit} thì nhập hàng: Nhà cung cấp: Kho điều kiện; Mã SP: SP014; Số lượng: 2')
    assert reply['action_draft']['condition']['threshold'] == limit
    with cursor() as cur:
        cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=1 AND variant_id=14', (limit,))
    result = confirm(auth_client, reply)
    assert 'Điều kiện đã thay đổi' in result['answer'] and stock() == limit
    with cursor() as cur:
        cur.execute('SELECT status FROM chat_action_drafts WHERE id=%s', (reply['action_draft']['id'],))
        assert cur.fetchone()['status'] == 'draft'


def test_condition_false_never_creates_draft(auth_client, tool_cleanup):
    auth_client.login(2)
    reply = chat(auth_client, 'Tồn kho SP014 tại NT01, nếu dưới 0 thì nhập hàng: Nhà cung cấp: Kho điều kiện; Mã SP: SP014; Số lượng: 2')
    assert 'action_draft' not in reply
    assert 'Điều kiện không thỏa' in reply['steps'][0]['answer']


def test_caught_failure_rolls_back_actual_write_and_leaves_draft(auth_client, tool_cleanup, monkeypatch):
    auth_client.login(2)
    before = stock()
    reply = chat(auth_client, 'Nhập hàng: Nhà cung cấp: Kho lỗi; Mã SP: SP014; Số lượng: 2')
    def fails_after_write(*args):
        with cursor() as cur:
            cur.execute('UPDATE inventory SET quantity=quantity+2 WHERE branch_id=1 AND variant_id=14')
        raise OperationRejected('Giao dịch thử bị lỗi.')
    monkeypatch.setattr('chat_tools.run', fails_after_write)
    result = confirm(auth_client, reply)
    assert 'bị lỗi' in result['answer']
    assert stock() == before
    with cursor() as cur:
        cur.execute('SELECT status FROM chat_action_drafts WHERE id=%s', (reply['action_draft']['id'],))
        assert cur.fetchone()['status'] == 'draft'
