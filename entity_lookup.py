"""Resolve names only inside the current capability's backend permission scope."""
import re

from db import cursor
from dashboard_service import scope_filter
from operations_routes import OperationRejected
from question_language import normalize, product_patterns


REFERENCES = {'product_ref': 'variant_id', 'customer_ref': 'customer_id',
              'order_ref': 'id', 'appointment_ref': 'id'}


def candidates(tool, key, reference, session_id):
    # The caller has already checked the intent and capability. Each lookup still
    # intersects the permission used by the eventual mutation, not a broader read.
    if key == 'product_ref':
        patterns = product_patterns(reference)
        pattern = patterns[0] if len(patterns) == 1 else '%' + reference + '%'
        with cursor() as cur:
            cur.execute('SELECT variant_id AS id,model_name,variant_name FROM v_ai_products '
                        'WHERE CONCAT(model_name," ",variant_name) LIKE %s ORDER BY variant_id LIMIT 20', (pattern,))
            return [{'id': row['id'], 'label': row['model_name'] + ' · ' + row['variant_name']}
                    for row in cur.fetchall()]
    if key == 'customer_ref':
        code = 'booking:create' if tool == 'booking_create' else 'customer:read'
        where, params = scope_filter(code, 'u.home_branch_id', 'u.id')
        with cursor() as cur:
            cur.execute("SELECT u.id,u.full_name,u.phone FROM users u JOIN customer_profiles cp ON cp.user_id=u.id "
                        'WHERE ' + where + ' AND (u.full_name LIKE %s OR u.phone=%s OR u.email=%s OR cp.customer_code=%s) '
                        'ORDER BY u.id LIMIT 20', (*params, '%' + reference + '%', reference, reference, reference))
            return [{'id': r['id'], 'label': r['full_name'] + ' · ' + (r['phone'] or '')} for r in cur.fetchall()]
    if key == 'order_ref':
        filters, params = [], ()
        for code in ('order:read', 'invoice:export'):
            part, bind = scope_filter(code, 'o.branch_id', 'o.customer_id')
            filters.append(part); params += bind
        with cursor() as cur:
            cur.execute('SELECT o.id,u.full_name,b.code FROM orders o JOIN users u ON u.id=o.customer_id '
                        'JOIN branches b ON b.id=o.branch_id WHERE ' + ' AND '.join(filters) +
                        ' AND (u.full_name LIKE %s OR u.email=%s) ORDER BY o.id DESC LIMIT 20',
                        (*params, '%' + reference + '%', reference))
            return [{'id': r['id'], 'label': f"Đơn #{r['id']} · {r['full_name']} · {r['code']}"} for r in cur.fetchall()]
    if key == 'appointment_ref':
        from chat_tools import run
        rows = run('appointment_list' if tool == 'appointment_update' else 'booking_list', {}, session_id)['rows']
        return [{'id': r['id'], 'label': f"Lịch #{r['id']} · {r['scheduled_at']} · {r['status']}"}
                for r in rows if normalize(reference) in normalize(str(r.get('full_name', r.get('customer_name', ''))))]
    raise OperationRejected('Tham chiếu không hợp lệ.')


def resolve_references(tool, raw, state, session_id, question):
    values = dict(raw)
    if tool == 'stock_receive' and not values.get('variant_id') and not values.get('items') and product_patterns(question):
        values.setdefault('product_ref', question)
    if tool == 'catalog_save' and not values.get('id') and product_patterns(question) and re.search(
            r'\b(?:sua|doi|cap nhat|dieu chinh)\b', normalize(question)):
        values.setdefault('product_ref', question)
    # Labeled names are references, never coerced into fabricated numeric IDs.
    for ref, key in REFERENCES.items():
        if key in values and isinstance(values[key], str) and not re.fullmatch(r'(?:SP|KH)?\d+', values[key], re.I):
            if ref == 'customer_ref' or ref == 'product_ref' and tool == 'stock_receive':
                values[ref] = values.pop(key)
    for ref, key in REFERENCES.items():
        if ref not in values:
            continue
        if ref == 'product_ref' and tool == 'catalog_save':
            key = 'id'
        matches = candidates(tool, ref, str(values[ref]), session_id)
        selected = state.get('selected', {}).get(ref)
        if selected:
            matches = [r for r in matches if r['id'] == selected]
        if len(matches) != 1:
            state.update(arguments=values, selection={'reference': ref, 'options': matches})
            return None, {'type': 'clarification', 'rows': [],
                          'answer': 'Cần chọn đúng đối tượng trong phạm vi được cấp.' if matches else
                                    'Chưa xác định được đối tượng phù hợp trong phạm vi được cấp. Hãy cung cấp mã hoặc tên rõ hơn.',
                          'clarification': {'tool': tool, 'options': matches, 'reference': ref}}
        values[key] = matches[0]['id']
        state.setdefault('entities', {})[key] = matches[0]['id']
        values.pop(ref)
    state.pop('selection', None)
    state.pop('selected', None)
    return values, None
