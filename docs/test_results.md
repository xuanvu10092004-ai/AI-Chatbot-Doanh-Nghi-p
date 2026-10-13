# Kết quả nghiệm thu Honda AI Portal M1–M6

Ngày kiểm chứng: 13/10/2026. Môi trường: Windows, Python 3.13, MariaDB 10.4.32 (XAMPP), Groq openai/gpt-oss-20b.

## Kiểm chứng cuối

```text
python init_db.py --reset
Applied 02_ai_views.sql
Applied 03_chatbot_ro_user.sql
Applied 04_indexes.sql
Applied 05_ai_product_details.sql
Applied 06_auth_dynamic_rbac.sql
Applied 07_own_scope_views.sql
MySQL schema and seed completed.
products: 10 (expected 10)
product_variants: 28 (expected 28)
inventory: 84 (expected 84)
customers: 80 (expected 80)
customer_profiles: 80 (expected 80)
orders: 30 (expected 30)
```

Lần reset thứ hai có cùng kết quả. `--extensions-only` bỏ qua cả sáu extension đã ghi trong `schema_migrations` và giữ đúng số dòng.

```text
python -m pytest -q
125 passed in 10.38s
```

Không có test skip trong lần kiểm chứng cuối. Các test Groq chỉ dùng payload sản phẩm/tồn kho/tài liệu public đã được người dùng cho phép. Một lần chạy trước có 1 fail do model hỏi lại chi nhánh cho câu GROUP BY đủ rõ; đã sửa prompt bằng ví dụ hợp lệ từ schema được phép, giữ nguyên test và assertion, sau đó bộ test cuối pass.

`git diff --check`, kiểm tra cú pháp bốn file JavaScript và so sánh schema chuẩn đều đạt. Quét source/template cấu hình không phát hiện khóa Groq thật trong Git.

## Mốc và bằng chứng

| Mốc | Hoàn thành | Kiểm chứng |
|---|---|---|
| M1 | Migration có ledger, auth columns, RBAC scope, nav, audit/version, user honda_app, demo password hash | Reset hai lần, counts đúng; honda_app bị chặn CREATE TABLE |
| M2 | Login/guest/logout/password change, session fixation, CSRF, cookie/header, khóa 5 lần/15 phút, permission mỗi request | Redirect/401/403, khóa, hash giả an toàn, next, expiry, thu hồi quyền tức thời |
| M3 | 10 API widget scoped, KPI/biểu đồ, Chart.js local, widget bị ẩn nếu thiếu quyền | KPI NT01/NT02/toàn hệ thống so với SQL độc lập; technician không đọc doanh thu |
| M4 | CRUD tài khoản/role, clone, ma trận quyền, description, audit filters, transaction/version/invariants | Cấp/gỡ quyền request kế tiếp; chặn system role/last admin/self-lock/nhiều branch; audit đầy đủ, rollback version |
| M5 | Bố cục Honda, menu động, landing theo priority, bảng nghiệp vụ scoped, chat dạng bảng/nguồn, responsive | Render các trang được phép 200, không được phép 403; menu technician/guest; Chrome headless ảnh login |
| M6 | Hai reset, test tổng, route audit, cấu hình/tài liệu, source nguyên vẹn | 125 pass; HTTP thật; file secrets không commit |

## HTTP thật bằng đăng nhập sales NT01

| Kiểm tra | Kết quả |
|---|---|
| POST /login có CSRF và mật khẩu demo từ .env | Đến /dashboard, HTTP 200 |
| /api/dashboard/orders | 13 đơn; doanh thu thuần 618.900.000 VNĐ |
| /api/dashboard/inventory | 154 xe; 3 dòng tồn kho bằng 0 |
| /api/customers, /inventory, /chat | 200, theo scope NT01 |
| POST /chat: giá Vario 160 | 200, ba dòng dữ liệu có cấu trúc |
| /admin/roles bằng sales | 403 |
| /static/vendor/chart.umd.js | 200 |

Ảnh kiểm tra trình duyệt: [Trang đăng nhập](images/portal_login.png). Đã kiểm tra bố cục ảnh thật. Chưa tự động hóa tương tác toàn bộ dashboard/admin trên trình duyệt; các luồng có kiểm tra HTTP/test client và JS syntax.

## Bảng route, quyền và scope

[Bảng đầy đủ tự sinh từ app.url_map](routes_permissions.md).

- Trang chưa đăng nhập chuyển về /login, API trả 401. Guest chỉ vào chat; root chỉ chuyển đến chat.
- Dashboard yêu cầu dashboard:view; API widget yêu cầu permission riêng, lọc all/branch/own. Widget tài chính cần đồng thời dashboard:finance và price:cost:read.
- Customers và inventory yêu cầu permission tương ứng, lọc branch/own, tìm kiếm/phân trang/sort whitelist.
- Admin users/lookups: user:manage; roles/permissions: rbac:manage; audit: audit:read. Các thao tác ghi có CSRF.
- Thay đổi quyền/role/gán role được serialize, transaction, before/after JSON và version. Không lưu mật khẩu/hash vào audit.
- Opportunity/Quote/Booking được bảo vệ quyền và giữ HTTP 501.

## File thêm/sửa

Thêm:
- data/schema/extensions/06_auth_dynamic_rbac.sql, 07_own_scope_views.sql
- scripts/seed_demo_passwords.py
- security.py, auth_routes.py, dashboard_service.py, dashboard_routes.py, admin_service.py, admin_routes.py, business_routes.py
- templates/base.html, login.html, change_password.html, error.html, dashboard.html, admin.html, records.html, soon.html
- static/portal.css, chat.js, dashboard.js, admin.js, records.js, vendor/chart.umd.js
- tests/conftest.py, test_auth.py, test_dashboard.py, test_admin.py, test_portal.py, test_rbac_safety.py
- docs/routes_permissions.md, docs/images/portal_login.png

Sửa: app.py, init_db.py, db.py, access_control.py, sql_service.py, llm_sql.py, templates/index.html, static/script.js, tests/test_chat_flow.py, tests/test_question_upgrade.py, .env.example, .gitignore, README.md, báo cáo này.

Skill/tài nguyên người dùng cung cấp được đưa vào Git như tài liệu tham chiếu; không sửa nội dung. .env cục bộ có các thông tin khởi tạo và không được commit.

## Quyết định thiết kế và giới hạn

1. Dùng extension 06 thay vì 05 vì 05 đã tồn tại; thêm 07 cho own scope. Không sửa schema chuẩn.
2. Dùng session Flask + CSRF token ngẫu nhiên và Werkzeug scrypt; không thêm framework auth/crypto.
3. Đọc quyền từ CSDL mỗi request, không dùng cache; version vẫn tăng để hỗ trợ cache tương lai.
4. RBAC cấu hình role/permission là toàn hệ thống nên rbac:manage phải scope all; branch/own fail closed. User management và audit áp scope tương ứng.
5. Guest được bật bằng ALLOW_GUEST_CHAT=true trong dev; có thể tắt bằng .env. Không còn header giả danh trong sản phẩm.
6. honda_app chỉ CRUD. chatbot_ro có SELECT view AI và EXECUTE hàm scope; không có quyền ghi/bảng gốc.
7. Demo id 1–9 dùng chung DEMO_ACCOUNT_PASSWORD từ .env, đã hash; tài khoản tạo mới bắt buộc đổi mật khẩu tạm.
8. Chưa kiểm chứng MySQL 8/ngram hoặc triển khai production. MariaDB và server dev cục bộ đã kiểm chứng.
9. Opportunity/Quote/Booking vẫn chưa có schema; không tự tạo. Câu chatbot ngoài dữ liệu/quyền hoặc mơ hồ không được bịa câu trả lời.

Các quyết định trên được ghi rõ để người dùng xem xét; không cần khởi động lại để thay đổi RBAC trong giao diện quản trị.
