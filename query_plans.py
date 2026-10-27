import re  # Nhan dien ma chi nhanh trong cau hoi ton kho.

from query_planner import plan_query as legacy_plan_query, NeedsGeneratedQuery  # Dung planner cu cho cac intent khac ton kho.
from question_language import normalize, product_pattern, asks_available_stock  # Chuan hoa cau hoi va nhan dien mau xe, tinh trang con hang.
from inventory_policy import asks_low_stock, LOW_STOCK_THRESHOLD  # Xac dinh xe sap het hang theo nguong dung chung.


def plan_query(question: str, intent: str) -> tuple[str, tuple]:
    # Lap truy van ton kho theo chi nhanh, mau xe va trang thai hang.
    # Cac intent khac duoc chuyen sang planner cu de giu tuong thich.
    if intent != 'ask_stock':
        return legacy_plan_query(question, intent)

    q = normalize(question)
    conditions, params = [], []

    # Loc theo ma chi nhanh cu the hoac theo khu vuc duoc neu trong cau hoi.
    branch = re.search(r'\b(nt01|nt02|cr01)\b', q)
    if branch:
        conditions.append('branch_code = %s'); params.append(branch.group(1).upper())
    elif 'nha trang' in q:
        conditions.append('branch_code IN (%s, %s)'); params.extend(('NT01', 'NT02'))
    elif 'cam ranh' in q:
        conditions.append('branch_code = %s'); params.append('CR01')

    # Neu co ten mau xe, them dieu kien tim kiem theo ten mau.
    pattern = product_pattern(question)
    if pattern:
        conditions.append('model_name LIKE %s'); params.append(pattern)

    # Phan biet xe sap het hang, het hang, yeu cau dem va xem chi tiet.
    low = asks_low_stock(question)
    empty = not low and ('het hang' in q or 'bang 0' in q)
    count = any(term in q for term in ('bao nhieu', 'tong so', 'may phien ban', 'may chiec', 'may xe', 'so luong', 'how many', 'tong ton'))
    detail = any(term in q for term in ('chi tiet', 'theo san pham', 'theo mau', 'theo chi nhanh', 'day du'))
    if low:
        conditions.append('quantity > 0 AND quantity < %s'); params.append(LOW_STOCK_THRESHOLD)
    elif empty:
        conditions.append('quantity = 0')
    elif asks_available_stock(question) and not count:
        conditions.append('quantity > 0')

    # Chon cot tra ve: tinh tong so xe, dem ban ghi hoac liet ke chi tiet.
    if count and empty and not detail:
        aggregate = 'COUNT(*) AS empty_inventory_rows'
    elif count and ('dong' in q or 'ban ghi' in q):
        aggregate = 'COUNT(*) AS inventory_rows'
    elif count and not detail:
        aggregate = 'SUM(quantity) AS total_stock'
    else:
        aggregate = 'branch_code, branch_name, model_name, variant_name, quantity'

    sql = f'SELECT {aggregate} FROM v_ai_inventory'
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    if 'branch_code' in aggregate:
        sql += ' ORDER BY branch_code, model_name, variant_name'
    return sql, tuple(params)