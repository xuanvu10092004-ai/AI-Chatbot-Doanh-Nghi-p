"""Small, explicit workflow interpreter. Each mutation still requires its draft confirmation."""
import re

from flask import g

from db import cursor
from operations_routes import OperationRejected
from question_language import normalize


SEPARATOR = (r'\s+(?:rồi|roi|sau đó|sau do|tiếp theo|tiep theo|đồng thời|dong thoi|và|va)\s+'
             r'(?=(?:nhập hàng|nhap hang|xem |tra cứu |tra cuu |xuất |xuat |cập nhật |cap nhat |'
             r'tạo |tao |xóa |xoa |thanh toán |thanh toan |duyệt |duyet |đặt lịch |dat lich |hủy lịch |huy lich |danh sách |danh sach ))')


def parse_workflow(question):
    q = normalize(question)
    if ' neu ' in ' ' + q + ' ':
        # Conditional writes are supported only for an exact, authorized stock
        # cell, with a comparison rechecked under lock when confirming.
        match = re.fullmatch(r'(.+?)\s*[,;]?\s*neu\s+(?:ton kho\s+)?(duoi|tren|bang)\s+(\d+)\s*(?:xe\s*)?thi\s+(.+)', q)
        if not match:
            raise OperationRejected('Cần làm rõ điều kiện. Dùng “Tồn kho SP014 tại NT01, nếu dưới 5 thì nhập hàng: …”. Chưa ghi thay đổi.')
        product = re.search(r'\bsp\s*(\d+)\b', match[1])
        branch = re.search(r'\b(nt01|nt02|cr01)\b', match[1])
        if not product or not branch:
            raise OperationRejected('Điều kiện cần đúng một mã SP và mã chi nhánh. Chưa ghi thay đổi.')
        # Split the original text to preserve names/notes and accents.
        action = re.split(r'\s+(?:thì|thi)\s+', question, maxsplit=1, flags=re.I)[-1]
        return [{'question': action, 'condition': {'variant_id': int(product[1]),
                 'branch_code': branch[1].upper(), 'operator': match[2], 'threshold': int(match[3])}}]
    steps = re.split(SEPARATOR, question, flags=re.I)
    if len(steps) > 5:
        raise OperationRejected('Mỗi quy trình tối đa 5 bước. Hãy chia nhỏ yêu cầu.')
    return [{'question': step} for step in steps] if len(steps) > 1 else None


def check_condition(condition, lock=False):
    from security import permissions
    grant = permissions().get('inventory:read')
    if not grant or grant['scope'] not in {'all', 'branch'}:
        raise OperationRejected('Tôi không thể hỗ trợ yêu cầu này.', 403)
    with cursor() as cur:
        cur.execute('SELECT id FROM branches WHERE code=%s', (condition['branch_code'],))
        branch = cur.fetchone()
        if not branch or grant['scope'] == 'branch' and branch['id'] != grant['branch']:
            raise OperationRejected('Tôi không thể hỗ trợ yêu cầu này.', 403)
        cur.execute('SELECT quantity FROM inventory WHERE branch_id=%s AND variant_id=%s' +
                    (' FOR UPDATE' if lock else ''), (branch['id'], condition['variant_id']))
        row = cur.fetchone()
    if row is None:
        raise OperationRejected('Chưa có đủ bằng chứng để kiểm tra điều kiện.')
    value, limit = row['quantity'], condition['threshold']
    matched = {'duoi': value < limit, 'tren': value > limit, 'bang': value == limit}[condition['operator']]
    return matched, value


def start_workflow(question, state, session_id):
    from chat_tools import available_tools, allowed
    from intent_resolver import resolve
    steps = parse_workflow(question)
    if not steps:
        return False
    # Validate/authorize the whole sequence before the first retrieval or draft.
    catalog = available_tools()
    for step in steps:
        resolution = resolve(step['question'], {}, catalog)
        if resolution.tool is None or resolution.tool == 'customer_input':
            raise OperationRejected('Cần làm rõ từng bước bằng tên lệnh. Nhập khách hàng cần dùng bản nháp riêng. Chưa ghi thay đổi.')
        ok, _ = allowed(resolution.tool, session_id)
        if not ok:
            raise OperationRejected('Tôi không thể hỗ trợ yêu cầu này.', 403)
        if step.get('condition'):
            from access_control import authorize_intent
            access = authorize_intent(session_id, g.user['id'] if g.user else None, 'ask_stock')
            if not access['allowed']:
                raise OperationRejected('Tôi không thể hỗ trợ yêu cầu này.', 403)
    state['workflow'] = {'remaining': steps, 'completed': []}
    return True


def advance_workflow(state, session_id, execute):
    workflow = state['workflow']
    reply = None
    while workflow['remaining']:
        step = workflow['remaining'][0]
        if step.get('condition'):
            matched, quantity = check_condition(step['condition'])
            if not matched:
                workflow['completed'].append({'answer': f'Điều kiện không thỏa (tồn kho: {quantity} xe). Không tạo lệnh ghi.', 'rows': []})
                workflow['remaining'].pop(0)
                continue
        reply = execute(step['question'])
        if reply is None:
            raise OperationRejected('Bước này chưa xác định được công cụ. Chưa thực thi bước tiếp theo.')
        if reply.get('action_draft'):
            draft = reply['action_draft']
            if step.get('condition'):
                import json
                with cursor() as cur:
                    cur.execute('SELECT arguments_json FROM chat_action_drafts WHERE id=%s FOR UPDATE', (draft['id'],))
                    args = json.loads(cur.fetchone()['arguments_json'])
                    args['_condition'] = step['condition']
                    cur.execute('UPDATE chat_action_drafts SET arguments_json=%s WHERE id=%s',
                                (json.dumps(args, ensure_ascii=False), draft['id']))
                draft['condition'] = step['condition']
            workflow['waiting_action'] = draft['id']
            break
        if reply.get('type') == 'clarification' or reply.get('access_denied'):
            break
        workflow['completed'].append(reply)
        workflow['remaining'].pop(0)
    if not workflow['remaining']:
        reply = dict(reply) if reply else {'type': 'tool', 'answer': 'Đã kết thúc quy trình.', 'rows': []}
        reply['steps'] = workflow['completed']
        state.pop('workflow', None)
    else:
        reply['steps'] = workflow['completed']
        reply['workflow'] = {'remaining': len(workflow['remaining']), 'requires_confirmation': bool(workflow.get('waiting_action'))}
    return reply
