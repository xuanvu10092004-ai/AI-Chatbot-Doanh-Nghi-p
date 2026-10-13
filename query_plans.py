"""Truy vấn tham số hóa cho các câu hỏi phổ biến, không cần API key."""
import re


def plan_query(question: str, intent: str) -> tuple[str, tuple]:
    q = question.casefold()
    count = any(w in q for w in ("bao nhiêu", "tổng số", "tong so", "how many"))
    branch = re.search(r"\b(nt01|nt02|cr01)\b", q)
    branch_code = branch.group(1).upper() if branch else None
    if intent == 'ask_customer_info':
        if 'đã mua' in q or 'da mua' in q:
            return 'SELECT COUNT(*) AS purchased_customers FROM v_ai_customers WHERE customer_status = %s', ('Đã mua',)
        if 'trả góp' in q or 'tra gop' in q:
            return 'SELECT COUNT(*) AS installment_customers FROM v_ai_customers WHERE payment_preference = %s', ('Trả góp',)
        if count:
            return 'SELECT COUNT(*) AS customers FROM v_ai_customers', ()
        return 'SELECT customer_id, full_name, customer_status, home_branch_code FROM v_ai_customers', ()
    if intent == 'ask_order_status':
        aggregate = 'SUM(net_amount) AS net_revenue' if 'doanh thu' in q else 'COUNT(DISTINCT order_id) AS orders' if count else '*'
        sql = f'SELECT {aggregate} FROM v_ai_orders'
        return (sql + ' WHERE branch_code = %s', (branch_code,)) if branch_code else (sql, ())
    if intent == 'ask_stock':
        if 'hết hàng' in q or 'het hang' in q or 'bằng 0' in q:
            return 'SELECT COUNT(*) AS empty_inventory_rows FROM v_ai_inventory WHERE quantity = 0', ()
        aggregate = 'SUM(quantity) AS total_stock' if 'tổng tồn' in q or 'tong ton' in q else 'COUNT(*) AS inventory_rows' if count else '*'
        sql = f'SELECT {aggregate} FROM v_ai_inventory'
        return (sql + ' WHERE branch_code = %s', (branch_code,)) if branch_code else (sql, ())
    view = 'v_ai_product_costs' if intent == 'ask_cost_margin' else 'v_ai_products'
    if 'phân khúc' in q:
        return 'SELECT segment, COUNT(*) AS variants FROM v_ai_products GROUP BY segment ORDER BY segment', ()
    if 'cao nhất' in q:
        return 'SELECT model_name, variant_name, list_price FROM v_ai_products ORDER BY list_price DESC LIMIT 1', ()
    for synonym, segment in (('xe ga','tay_ga'), ('tay ga','tay_ga'), ('xe số','xe_so'), ('xe côn','con_tay')):
        if synonym in q:
            return 'SELECT model_name, variant_name, list_price FROM v_ai_products WHERE segment = %s ORDER BY model_name, list_price', (segment,)
    # Chỉ lấy phần tên người dùng nhập làm giá trị tham số, không ghép vào SQL.
    match = re.search(r'\b(sh\s*160i|vision\s*110|rebel\s*500|wave[^?]*?|air blade\s*\d*|winner[^?]*?)\b', q)
    pattern = '%' + match.group(0) + '%' if match else None
    if pattern:
        if count and intent != 'ask_cost_margin' and not any(w in q for w in ('giá', 'gia')):
            return 'SELECT COUNT(*) AS variants FROM v_ai_products WHERE model_name LIKE %s', (pattern,)
        sql = f'SELECT * FROM {view} WHERE model_name LIKE %s ORDER BY list_price'
        return sql, (pattern,)
    if count and intent != 'ask_cost_margin':
        return 'SELECT COUNT(*) AS variants FROM v_ai_products', ()
    if any(w in q for w in ('giá', 'gia', 'mẫu xe', 'phiên bản', 'danh sách')):
        return f'SELECT * FROM {view} ORDER BY model_name, list_price', ()
    return 'SELECT model_name FROM v_ai_products WHERE 1 = 0', ()
