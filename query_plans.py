import re  # Nhận diện branch code và số liệu trong câu hỏi tồn kho.

from query_planner import plan_query as legacy_plan_query, NeedsGeneratedQuery  # Dùng lại plan cũ cho intent không phải tồn kho.
from question_language import normalize, product_pattern, asks_available_stock  # Chuẩn hóa ngôn ngữ và nhận diện xe/tồn khả dụng.
from inventory_policy import asks_low_stock, LOW_STOCK_THRESHOLD  # Áp quy ước xe sắp hết hàng thống nhất.


def plan_query(question: str, intent: str) -> tuple[str, tuple]:
    # Tạo truy vấn tồn kho theo chi nhánh/xe/trạng thái; intent khác chuyển sang planner cũ.
    if intent != 'ask_stock':
        return legacy_plan_query(question, intent)

    q = normalize(question)
    conditions, params = [], []
    branch = re.search(r'\b(nt01|nt02|cr01)\b', q)
    if branch:
        conditions.append('branch_code = %s'); params.append(branch.group(1).upper())
    elif 'nha trang' in q:
        conditions.append('branch_code IN (%s, %s)'); params.extend(('NT01', 'NT02'))
    elif 'cam ranh' in q:
        conditions.append('branch_code = %s'); params.append('CR01')
    pattern = product_pattern(question)
    if pattern:
        conditions.append('model_name LIKE %s'); params.append(pattern)

    low = asks_low_stock(question)
    empty = not low and ('het hang' in q or 'bang 0' in q)
    count = any(term in q for term in ('bao nhieu', 'tong so', 'may phien ban', 'may chiec', 'may xe', 'so luong', 'how many'))
    detail = 'chi tiet' in q or 'theo san pham' in q or 'theo mau' in q
    if low:
        conditions.append('quantity > 0 AND quantity < %s'); params.append(LOW_STOCK_THRESHOLD)
    elif empty:
        conditions.append('quantity = 0')
    elif asks_available_stock(question) and not count:
        conditions.append('quantity > 0')

    if count and not detail:
        aggregate = 'SUM(quantity) AS total_stock'
    elif count and ('dong' in q or 'ban ghi' in q):
        aggregate = 'COUNT(*) AS inventory_rows'
    else:
        aggregate = 'branch_code, branch_name, model_name, variant_name, quantity'
    sql = f'SELECT {aggregate} FROM v_ai_inventory'
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    if 'branch_code' in aggregate:
        sql += ' ORDER BY branch_code, model_name, variant_name'
    return sql, tuple(params)
