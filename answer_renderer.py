"""Hiển thị kết quả SQL chính xác, không để model viết lại giá/số lượng."""
from decimal import Decimal


LABELS = {
    'model_name': 'Mẫu xe', 'variant_name': 'Phiên bản', 'color': 'Màu',
    'segment': 'Phân khúc', 'engine_cc': 'Dung tích động cơ',
    'list_price': 'Giá niêm yết', 'cost_price': 'Giá vốn', 'gross_margin': 'Lợi nhuận gộp',
    'total_stock': 'Tổng số xe tồn', 'quantity': 'Số lượng xe',
    'fuel_consumption_l100km': 'Tiêu hao nhiên liệu', 'description': 'Mô tả',
    'engine_type': 'Động cơ', 'fuel_tank_l': 'Dung tích bình xăng',
    'weight_kg': 'Khối lượng', 'brake_type': 'Phanh', 'warranty': 'Bảo hành',
    'branch_code': 'Mã chi nhánh', 'branch_name': 'Chi nhánh',
    'variants': 'Số phiên bản', 'customers': 'Số khách hàng', 'orders': 'Số đơn hàng',
    'purchased_customers': 'Khách đã mua', 'installment_customers': 'Khách trả góp',
    'net_revenue': 'Doanh thu thuần', 'min_price': 'Giá thấp nhất', 'max_price': 'Giá cao nhất',
    'empty_inventory_rows': 'Dòng tồn kho hết hàng', 'customer_status': 'Trạng thái khách hàng',
    'full_name': 'Họ tên', 'customer_name': 'Khách hàng', 'status': 'Trạng thái',
    'home_branch_code': 'Chi nhánh của khách', 'phone': 'Số điện thoại', 'email': 'Email',
    'order_id': 'Mã đơn', 'customer_id': 'Mã khách', 'unit_price': 'Đơn giá',
    'discount_amount': 'Giảm giá', 'line_amount': 'Thành tiền trước giảm', 'net_amount': 'Thành tiền sau giảm',
}


def display_value(key, value):
    if value is None:
        return 'Chưa có dữ liệu'
    if key == 'segment':
        return {'tay_ga': 'Xe ga', 'xe_so': 'Xe số', 'con_tay': 'Xe côn tay'}.get(value, value)
    if isinstance(value, (int, float, Decimal)) and any(w in key for w in ('price', 'amount', 'revenue', 'margin')):
        amount = Decimal(str(value))
        formatted = f'{amount:,.0f}' if amount == amount.to_integral() else f'{amount:,.2f}'
        formatted = formatted.replace(',', '_').replace('.', ',').replace('_', '.')
        return formatted + ' VNĐ'
    unit = {'engine_cc': ' cc', 'fuel_consumption_l100km': ' lít/100 km', 'fuel_tank_l': ' lít', 'weight_kg': ' kg'}.get(key, '')
    return str(value) + unit


def render_rows(rows: list[dict]) -> str:
    blocks = []
    for row in rows:
        lines = []
        for key, value in row.items():
            if key in {'product_id', 'variant_id'}:
                continue
            lines.append(f'{LABELS.get(key, key)}: {display_value(key, value)}')
        blocks.append('\n'.join(lines))
    return 'Kết quả từ dữ liệu mô phỏng:\n\n' + '\n\n'.join(blocks)


class QueryEvidence(str):
    def __new__(cls, text: str, rows: list[dict], generated: bool = False, summary: str | None = None):
        instance = super().__new__(cls, text)
        instance.rows = rows
        instance.display = (summary + '\n\n' if summary else '') + render_rows(rows)
        instance.engine = 'groq-sql' if generated else 'database'
        instance.summary = summary or f'Tìm thấy {len(rows)} dòng kết quả trong dữ liệu được phép truy cập.'
        return instance
