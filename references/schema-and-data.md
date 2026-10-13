# Schema, dữ liệu và ma trận quyền (đã kiểm chứng)

Mọi con số dưới đây lấy từ lần chạy thật `honda_chatbot_rbac.sql` rồi `honda_import_data.sql` rồi `02_ai_views.sql` trên MariaDB 10.11. Chưa kiểm chứng trên MySQL 8, nên bước kiểm tra trên MySQL 8 vẫn phải làm.

## Mục lục
1. Bốn file nguồn
2. Bảng và quan hệ chính
3. Quy ước mã định danh
4. Role, permission, user mẫu
5. Intent của chatbot
6. Tài liệu tri thức (kb_documents)
7. Số dòng kỳ vọng sau khi nạp
8. Lệnh Windows

## 1. Bốn file nguồn

| File | Vai trò | Ghi chú |
|---|---|---|
| `honda_chatbot_rbac.sql` | Schema chuẩn + dữ liệu mẫu nhỏ + truy vấn minh họa | Có `DROP DATABASE honda_chatbot`. KHÔNG sửa. Chạy trước. |
| `honda_import_data.sql` | Nạp dữ liệu từ Excel | Tự xóa dữ liệu mẫu cũ rồi nạp. Tạo thêm bảng `product_specs`, `customer_profiles`. Chạy sau schema. |
| `honda_dataset_khach_hang_san_pham.xlsx` | Nguồn gốc dữ liệu (sheet Khach_hang, San_pham, Ton_kho, Ghi_chu) | Cột công thức là dữ liệu dẫn xuất, không nạp. |
| `import_excel_to_sql.py` | Sinh lại `honda_import_data.sql` từ Excel | Đọc cột "Số điện thoại" bằng `dtype=str` để không mất số 0 đầu. |

## 2. Bảng và quan hệ chính

- Nhóm RBAC: `branches`, `users`, `roles`, `permissions`, `user_roles(user_id, role_id, scope_branch_id, granted_by)`, `role_permissions`.
- Nghiệp vụ: `products`, `product_variants(list_price, cost_price)`, `inventory(branch_id, variant_id, quantity)`, `orders` (ràng buộc `chk_sod`: `approved_by <> created_by`), `order_items`.
- Bổ sung bởi file import: `product_specs(product_id ...)`, `customer_profiles(user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status)`.
- Chatbot: `kb_categories(required_permission_id)`, `kb_documents(category_id, branch_id)`, `chatbot_intents(required_permission_id, data_source)`, `chat_sessions(user_id NULL = guest)`, `chat_messages`, `chatbot_audit_log(decision allowed|denied)`.
- View có sẵn: `v_user_permissions(user_id, role_name, permission_code, scope_branch_id)`, `v_user_kb_access(user_id, doc_id, title, category)`.
- Do skill này thêm (xem `assets/02_ai_views.sql`): `v_ai_products`, `v_ai_inventory`, `v_ai_customers`, `v_ai_orders`, `v_ai_product_costs`, hàm `fn_session_branch()`, bảng `ai_view_registry`, `ai_data_dictionary`.

Không có bảng cho Opportunity, Quote, Booking và cột `company` của khách hàng. Đừng tự tạo (xem quy tắc trong SKILL.md).

## 3. Quy ước mã định danh

- `product_variants.id` = số trong mã SP (SP012 là id 12). `products.id` 1 đến 10 theo thứ tự mẫu xe.
- Khách hàng: `KH0001` có `users.id = 101`, `KH0080` có `users.id = 180` (id = 100 + số thứ tự). Hai user khách mẫu id 8, 9 từ file schema KHÔNG có hồ sơ nên không xuất hiện trong `v_ai_customers`. Điều này là bình thường.
- Chi nhánh: `1 = NT01`, `2 = NT02`, `3 = CR01`.
- Đơn hàng id 1 đến 30, đều `delivered`, `created_by` là 3 hoặc 4, `approved_by = 2`.

## 4. Role, permission, user mẫu

Permission: 1 `chatbot:use`, 2 `kb:public:read`, 3 `kb:sales:read`, 4 `kb:technical:read`, 5 `kb:finance:read`, 6 `kb:internal:read`, 7 `inventory:read`, 8 `order:read`, 9 `order:create`, 10 `order:approve`, 11 `customer:read`, 12 `price:cost:read`, 13 `kb:manage`, 14 `user:manage`, 15 `audit:read`, 16 `discount:approve`.

| Role (id) | Permission |
|---|---|
| super_admin (1) | tất cả |
| branch_manager (2) | 1,2,3,4,6,7,8,9,10,11,16 |
| sales_staff (3) | 1,2,3,7,8,9,11 |
| technician (4) | 1,2,4,7 |
| accountant (5) | 1,2,5,8,12 |
| marketing (6) | 1,2,3,13 |
| customer (7) | 1,2 |
| guest (8) | 2 |

User mẫu (role, phạm vi chi nhánh): 1 admin (super_admin, toàn hệ thống); 2 Nguyễn Văn Minh (branch_manager, NT01); 3 Trần Thị Lan (sales_staff, NT01); 4 Lê Quốc Bảo (sales_staff, NT02); 5 Phạm Văn Hùng (technician, NT01); 6 Võ Thị Hoa (accountant, toàn hệ thống); 7 marketing (toàn hệ thống); 8, 9 khách hàng.

Lưu ý thiết kế cần báo người dùng: role `customer` KHÔNG có `order:read`, nên khách không hỏi được đơn hàng qua text-to-SQL. Dòng audit mẫu trong schema ghi "customer 8 được phép ask_order_status" mâu thuẫn với ma trận này. Tra cứu "đơn của tôi" phải đi qua truy vấn tham số hóa cố định `WHERE customer_id = <user_id của phiên>`, và cần người dùng quyết định có thêm permission `order:read_own` hay không.

## 5. Intent của chatbot (bảng `chatbot_intents`)

| id | code | Permission cần | Nguồn dữ liệu |
|---|---|---|---|
| 1 | ask_price_list | kb:public:read | product_variants (list_price) |
| 2 | ask_promotion | kb:public:read | kb_documents public |
| 3 | ask_stock | inventory:read | inventory |
| 4 | ask_order_status | order:read | orders |
| 5 | ask_customer_info | customer:read | users, customer_profiles |
| 6 | ask_sales_policy | kb:sales:read | kb_documents sales |
| 7 | ask_tech_procedure | kb:technical:read | kb_documents technical |
| 8 | ask_cost_margin | price:cost:read | product_variants (cost_price) |
| 9 | ask_finance_procedure | kb:finance:read | kb_documents finance |
| 10 | ask_hr_policy | kb:internal:read | kb_documents internal |
| 11 | view_audit_log | audit:read | chatbot_audit_log |

## 6. Tài liệu tri thức

Danh mục: 1 public (kb:public:read), 2 sales (kb:sales:read), 3 technical (kb:technical:read), 4 finance (kb:finance:read), 5 internal (kb:internal:read). Tài liệu 1 đến 4 là public (giá niêm yết, thủ tục mua xe, trả góp, lịch bảo dưỡng); 5 là khuyến mãi chỉ của NT01 (`branch_id = 1`); 6, 7 sales; 8, 9 technical; 10 finance; 11 internal.

Nội dung một số tài liệu có dấu chấm phẩy bên trong chuỗi, ví dụ tài liệu 1. Vì vậy KHÔNG được tách file SQL bằng `split(';')`.

## 7. Số dòng kỳ vọng sau khi nạp

`products` 10, `product_variants` 28, `inventory` 84, khách hàng (`users.id > 100`) 80, `customer_profiles` 80, `orders` 30, `order_items` 30.

## 8. Lệnh Windows

PowerShell không hỗ trợ toán tử `<`. Dùng lệnh `source` của mysql client (dấu `/` trong đường dẫn) hoặc gọi mysql CLI bằng subprocess và đẩy file vào stdin:

```
mysql -u root -p --default-character-set=utf8mb4 -e "source D:/Projects/thuc_tap/project_thuc_tap/data/schema/honda_chatbot_rbac.sql"
mysql -u root -p --default-character-set=utf8mb4 -e "source D:/Projects/thuc_tap/project_thuc_tap/data/seed/honda_import_data.sql"
```
