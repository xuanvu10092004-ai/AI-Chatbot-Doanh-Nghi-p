# Xuất các view dữ liệu đã đồng bộ ra workbook và thay file theo cách an toàn.
from __future__ import annotations

from datetime import date, datetime  # Tính tuổi khách và ghi thời điểm đồng bộ.
from pathlib import Path  # Xác định workbook nguồn, workbook xuất và file tạm.
import shutil  # Sao chép workbook xuất về nguồn sau khi hoàn tất.
from tempfile import NamedTemporaryFile  # Lưu workbook tạm rồi thay thế nguyên tử.
from typing import Any  # Mô tả tuple dữ liệu linh hoạt từ MySQL.

from db import cursor  # Mở cursor hoặc connection MySQL.

ROOT = Path(__file__).resolve().parent
SOURCE_WORKBOOK = ROOT / "data" / "source" / "honda_dataset_khach_hang_san_pham.xlsx"
SYNCED_WORKBOOK = ROOT / "data" / "exports" / "honda_chatbot_synced.xlsx"


# Báo workbook nguồn đang bị khóa để service trả trạng thái đồng bộ phù hợp.
class ExcelSourceLocked(RuntimeError):
    pass


def _age(value: Any) -> int | None:
    if not value:
        return None
    born = value.date() if isinstance(value, datetime) else value
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _rows() -> dict[str, list[tuple[Any, ...]]]:
    # Tạo ba sheet khách hàng, sản phẩm và tồn kho từ dữ liệu hiện tại trong MySQL.
    with cursor() as cur:
        cur.execute("""
            SELECT u.id AS customer_id, COALESCE(cp.customer_code, CONCAT('DB', LPAD(u.id, 4, '0'))) AS customer_code, u.full_name, cp.gender,
                   cp.birth_date, u.phone, u.email, cp.province, cp.district,
                   cp.address, cp.occupation, cp.lead_source, b.code AS branch_code,
                   p.model_name, cp.payment_preference, cp.registered_at, cp.status
            FROM users u
            JOIN customer_profiles cp ON cp.user_id = u.id
            LEFT JOIN branches b ON b.id = u.home_branch_id
            LEFT JOIN products p ON p.id = cp.interested_product_id
            WHERE u.user_type = 'customer'
            ORDER BY cp.customer_code, u.id
        """)
        customers = cur.fetchall()

        cur.execute("""
            SELECT o.customer_id, oi.variant_id, oi.unit_price
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status <> 'cancelled'
            ORDER BY o.created_at DESC
        """)
        purchases: dict[int, dict[str, Any]] = {}
        for row in cur.fetchall():
            purchases.setdefault(row["customer_id"], row)

        customer_rows = []
        for row in customers:
            purchase = purchases.get(row["customer_id"])
            customer_rows.append((
                row["customer_code"], row["full_name"], row["gender"], row["birth_date"],
                _age(row["birth_date"]), row["phone"], row["email"], row["province"],
                row["district"], row["address"], row["occupation"], row["lead_source"],
                row["branch_code"], row["model_name"], row["payment_preference"],
                row["registered_at"], row["status"],
                f"SP{purchase['variant_id']:03d}" if purchase else None,
                purchase["unit_price"] if purchase else None,
            ))

        cur.execute("""
            SELECT pv.id, p.model_name, pv.variant_name,
                   SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
                   p.segment, p.engine_cc, ps.engine_type, ps.fuel_tank_l,
                   ps.weight_kg, p.fuel_consumption_l100km, ps.brake_type, ps.warranty,
                   pv.list_price, pv.cost_price, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM product_variants pv
            JOIN products p ON p.id = pv.product_id
            LEFT JOIN product_specs ps ON ps.product_id = p.id
            LEFT JOIN inventory i ON i.variant_id = pv.id
            GROUP BY pv.id, p.model_name, pv.variant_name, p.segment, p.engine_cc,
                     ps.engine_type, ps.fuel_tank_l, ps.weight_kg,
                     p.fuel_consumption_l100km, ps.brake_type, ps.warranty,
                     pv.list_price, pv.cost_price
            ORDER BY pv.id
        """)
        product_rows = []
        for row in cur.fetchall():
            price, cost = row["list_price"], row["cost_price"]
            product_rows.append((
                f"SP{row['id']:03d}", row["model_name"], row["variant_name"], row["color"],
                row["segment"], row["engine_cc"], row["engine_type"], row["fuel_tank_l"],
                row["weight_kg"], row["fuel_consumption_l100km"], row["brake_type"],
                row["warranty"], price, cost,
                price - cost if price is not None and cost is not None else None,
                (price - cost) / price if price else None, row["total_stock"],
            ))

        cur.execute("""
            SELECT pv.id, p.model_name, pv.variant_name,
                   SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
                   COALESCE(SUM(CASE WHEN b.code = 'NT01' THEN i.quantity ELSE 0 END), 0) AS nt01,
                   COALESCE(SUM(CASE WHEN b.code = 'NT02' THEN i.quantity ELSE 0 END), 0) AS nt02,
                   COALESCE(SUM(CASE WHEN b.code = 'CR01' THEN i.quantity ELSE 0 END), 0) AS cr01
            FROM product_variants pv
            JOIN products p ON p.id = pv.product_id
            LEFT JOIN inventory i ON i.variant_id = pv.id
            LEFT JOIN branches b ON b.id = i.branch_id
            GROUP BY pv.id, p.model_name, pv.variant_name
            ORDER BY pv.id
        """)
        inventory_rows = []
        for row in cur.fetchall():
            inventory_rows.append((
                f"SP{row['id']:03d}", row["model_name"],
                f"{row['variant_name']} - {row['color']}", row["nt01"], row["nt02"],
                row["cr01"], row["nt01"] + row["nt02"] + row["cr01"],
            ))

    return {"Khach_hang": customer_rows, "San_pham": product_rows, "Ton_kho": inventory_rows}


def export_synced_workbook(path: Path = SYNCED_WORKBOOK) -> Path:
    # Giữ header/style nguồn, ghi dữ liệu mới vào file tạm rồi thay đích.
    from openpyxl import Workbook, load_workbook  # Đọc hoặc tạo workbook Excel.
    from openpyxl.styles import Font  # Định dạng header trong workbook Excel.

    data = _rows()
    book = load_workbook(SOURCE_WORKBOOK) if SOURCE_WORKBOOK.exists() else Workbook()
    fallback_headers = {
        "Khach_hang": ["Mã KH", "Họ và tên", "Giới tính", "Ngày sinh", "Tuổi", "Số điện thoại", "Email", "Tỉnh/Thành phố", "Quận/Huyện", "Địa chỉ", "Nghề nghiệp", "Nguồn khách", "Chi nhánh phụ trách", "Mẫu xe quan tâm", "Hình thức thanh toán", "Ngày đăng ký", "Trạng thái", "Mã SP đã mua", "Giá trị mua (VNĐ)"],
        "San_pham": ["Mã SP", "Mẫu xe", "Phiên bản", "Màu sắc", "Phân khúc", "Dung tích (cc)", "Loại động cơ", "Dung tích bình xăng (L)", "Khối lượng (kg)", "Tiêu hao (L/100km)", "Phanh", "Bảo hành", "Giá niêm yết (VNĐ)", "Giá vốn (VNĐ)", "Lợi nhuận gộp (VNĐ)", "Biên lợi nhuận (%)", "Tồn kho toàn hệ thống"],
        "Ton_kho": ["Mã SP", "Mẫu xe", "Phiên bản - Màu", "NT01", "NT02", "CR01", "Tổng"],
    }
    for name, rows in data.items():
        sheet = book[name] if name in book.sheetnames else book.create_sheet(name)
        headers = [cell.value for cell in sheet[1]] if sheet.max_row else fallback_headers[name]
        sheet.delete_rows(1, sheet.max_row)
        sheet.append(headers or fallback_headers[name])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append(list(row))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for table in sheet.tables.values():
            table.ref = sheet.dimensions
    if "Ghi_chu" not in book.sheetnames:
        book.create_sheet("Ghi_chu")
    notes = book["Ghi_chu"]
    notes["A5"] = "Bản đồng bộ tự động từ CSDL chính"
    notes["B5"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(prefix=path.stem + ".", suffix=".xlsx", dir=path.parent, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        book.save(temp_path)
        temp_path.replace(path)
        if path.resolve() != SOURCE_WORKBOOK.resolve():
            try:
                shutil.copy2(path, SOURCE_WORKBOOK)
            except PermissionError as exc:
                raise ExcelSourceLocked(str(SOURCE_WORKBOOK)) from exc
    finally:
        temp_path.unlink(missing_ok=True)
    return path


def sync_after_commit() -> dict[str, Any]:
    from db import defer_until_commit
    if defer_until_commit(sync_after_commit):
        return {'status':'scheduled'}
    try:
        return {"status": "completed", "path": str(export_synced_workbook())}
    except ExcelSourceLocked:
        return {"status": "source_locked", "error": "Excel dang mo file nguon; hay dong Excel roi tai lai trang hoac luu lai du lieu."}
    except Exception as exc:
        return {"status": "failed", "error": type(exc).__name__}
