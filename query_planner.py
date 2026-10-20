"""Truy vấn cố định cho câu hỏi biến; câu phức tạp chuyển sang bộ sinh SQL."""
import re

from question_language import normalize, product_pattern, product_patterns, asks_available_stock
from inventory_policy import asks_low_stock, LOW_STOCK_THRESHOLD


class NeedsGeneratedQuery(ValueError):
    pass


def plan_query(question: str, intent: str) -> tuple[str, tuple]:
    q = normalize(question)
    patterns = product_patterns(question)
    simple_comparison = not any(term in q for term in (
        'trung binh', 'thap nhat', 'cao nhat', 'min(', 'max(', 'moi mau',
        'duoi ', 'tren ', 'sap xep', 'chi lay', 'khong lay', 'abs', 'cbs',
    ))
    if 'so sanh' in q and len(patterns) >= 2 and intent == 'ask_price_list' and simple_comparison:
        conditions = ' OR '.join('model_name LIKE %s' for _ in patterns)
        return ('SELECT model_name, variant_name, list_price, engine_cc, fuel_consumption_l100km, '
                'fuel_tank_l, weight_kg, brake_type, warranty FROM v_ai_products WHERE ('
                + conditions + ') ORDER BY model_name, list_price'), tuple(patterns)
    if intent != 'ask_stock' and any(w in q for w in ('so sanh', 'trung binh', 'theo thang', 'theo ngay', 'sap xep', 'dau tien', 'gan nhat', 'top ', 'duoi ', 'tren ', 'tu ', 'den ')):
        raise NeedsGeneratedQuery()
    count = any(w in q for w in ('bao nhieu', 'tong so', 'may phien ban', 'how many'))
    price = any(w in q for w in ('gia', 'bao nhieu tien', 'bao tien'))
    branch = re.search(r'\b(nt01|nt02|cr01)\b', q)
    branch_code = branch.group(1).upper() if branch else None
    pattern = product_pattern(question)
    if intent == 'ask_price_list':
        year = re.search(r'\b(?:doi|nam)\s+((?:19|20)\d{2})\b', q)
        lifecycle = 'previous' if 'doi cu' in q or 'doi truoc' in q else 'current' if 'doi moi' in q or 'hien hanh' in q else 'discontinued' if 'ngung kinh doanh' in q else None
        if year or lifecycle:
            filters, values = [], []
            if year: filters.append('model_year = %s'); values.append(int(year.group(1)))
            if lifecycle: filters.append('lifecycle = %s'); values.append(lifecycle)
            if pattern: filters.append('model_name LIKE %s'); values.append(pattern)
            return 'SELECT model_name,variant_name,model_year,lifecycle,list_price FROM v_ai_products WHERE ' + ' AND '.join(filters) + ' ORDER BY model_name,list_price', tuple(values)
    if intent == 'ask_customer_info':
        if 'da mua' in q: return 'SELECT COUNT(*) AS purchased_customers FROM v_ai_customers WHERE customer_status = %s', ('Đã mua',)
        if 'tra gop' in q: return 'SELECT COUNT(*) AS installment_customers FROM v_ai_customers WHERE payment_preference = %s', ('Trả góp',)
        if count: return 'SELECT COUNT(*) AS customers FROM v_ai_customers', ()
        if any(w in q for w in ('tiem nang', 'tu van', 'ngung lien he')):
            status = 'Tiềm năng' if 'tiem nang' in q else 'Đang tư vấn' if 'tu van' in q else 'Ngừng liên hệ'
            return 'SELECT customer_id, full_name, customer_status, home_branch_code FROM v_ai_customers WHERE customer_status = %s', (status,)
        raise NeedsGeneratedQuery()
    if intent == 'ask_order_status':
        aggregate = 'SUM(net_amount) AS net_revenue' if 'doanh thu' in q else 'COUNT(DISTINCT order_id) AS orders' if count else '*'
        sql = f'SELECT {aggregate} FROM v_ai_orders'
        return (sql + ' WHERE branch_code = %s', (branch_code,)) if branch_code else (sql, ())
    if intent == 'ask_stock':
        conditions, params = [], []
        if branch_code: conditions.append('branch_code = %s'); params.append(branch_code)
        elif 'nha trang' in q: conditions.append('branch_code IN (%s, %s)'); params.extend(('NT01', 'NT02'))
        elif 'cam ranh' in q: conditions.append('branch_code = %s'); params.append('CR01')
        if pattern: conditions.append('model_name LIKE %s'); params.append(pattern)
        low = asks_low_stock(question)
        empty = not low and ('het hang' in q or 'bang 0' in q)
        if low: conditions.append('quantity > 0 AND quantity < %s'); params.append(LOW_STOCK_THRESHOLD)
        elif empty: conditions.append('quantity = 0')
        elif asks_available_stock(question): conditions.append('quantity > 0')
        if empty and not low and count: aggregate = 'COUNT(*) AS empty_inventory_rows'
        elif count and ('dong' in q or 'ban ghi' in q): aggregate = 'COUNT(*) AS inventory_rows'
        elif (count or 'tong ton' in q) and not any(term in q for term in ('day du', 'theo san pham', 'theo chi nhanh', 'theo mau', 'chi tiet')): aggregate = 'SUM(quantity) AS total_stock'
        else: aggregate = 'branch_code, branch_name, model_name, variant_name, quantity'
        sql = f'SELECT {aggregate} FROM v_ai_inventory'
        sql += (' WHERE ' + ' AND '.join(conditions) if conditions else '')
        if 'branch_code' in aggregate: sql += ' ORDER BY branch_code, model_name, variant_name'
        return sql, tuple(params)
    view = 'v_ai_product_costs' if intent == 'ask_cost_margin' else 'v_ai_products'
    if 'phan khuc' in q and count: return 'SELECT segment, COUNT(*) AS variants FROM v_ai_products GROUP BY segment ORDER BY segment', ()
    if 'cao nhat' in q or 'dat nhat' in q or 're nhat' in q:
        direction = 'ASC' if 're nhat' in q else 'DESC'; condition = ' WHERE model_name LIKE %s' if pattern else ''
        return f'SELECT model_name, variant_name, list_price FROM v_ai_products{condition} ORDER BY list_price {direction} LIMIT 1', (pattern,) if pattern else ()
    if pattern:
        if count and not price and 'thong tin' not in q: return 'SELECT COUNT(*) AS variants FROM v_ai_products WHERE model_name LIKE %s', (pattern,)
        return f'SELECT * FROM {view} WHERE model_name LIKE %s ORDER BY list_price', (pattern,)
    for synonym, segment in (('xe ga', 'tay_ga'), ('tay ga', 'tay_ga'), ('xe so', 'xe_so'), ('xe con', 'con_tay')):
        if synonym in q: return 'SELECT model_name, variant_name, list_price FROM v_ai_products WHERE segment = %s ORDER BY model_name, list_price', (segment,)
    if count and not price: return 'SELECT COUNT(*) AS variants FROM v_ai_products', ()
    if q in ('gia xe', 'bang gia', 'gia cac mau xe', 'danh sach xe', 'danh sach mau xe'): return f'SELECT * FROM {view} ORDER BY model_name, list_price', ()
    raise NeedsGeneratedQuery()
