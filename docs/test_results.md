# Kiểm chứng logo, câu trả lời và tài khoản - 14/10/2026

Môi trường thực tế: Windows, Python 3.13, MariaDB 10.4.32, Groq dùng cấu hình .env. Không thay đổi schema chuẩn hoặc mật khẩu cấu hình.

## Kết quả lệnh thực tế

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

python -m pytest -q --tb=short
132 passed in 10.42s
```

Lần chạy đầu trong sandbox: 127 passed, 5 failed do Groq bị chặn mạng (WinError 10013). Xét duyệt tự động ban đầu từ chối gửi payload ra ngoài. Sau khi người dùng cho phép gửi schema view sản phẩm/tồn kho và dữ liệu mô phỏng đến Groq, chạy lại với mạng được phép: toàn bộ 132 test đạt, không skip. Không xóa test hoặc nới assertion.

## Kiểm tra bổ sung

| Hạng mục | Kết quả thực tế |
|---|---|
| Logo tại login và chat | HTTP 200, ảnh static khớp từng byte với ảnh gốc |
| Đậm/nghiêng, tiêu đề, danh sách | DOM có strong/em/ul/ol; không hiện dấu định dạng hoặc nhãn khối md |
| HTML độc hại trong câu trả lời | Không tạo thẻ script/img/link; không dùng innerHTML |
| Dấu gạch dài | Chuẩn hóa API, lịch sử bot, tiêu đề nguồn và ô bảng sang - |
| Khuyến mãi với admin và sales NT01 | Chỉ lấy tài liệu id 5, không lấy quy trình kỹ thuật id 8 hoặc trả góp id 3 |
| Khuyến mãi với guest | Không truy xuất được tài liệu sales |
| Cơ sở dữ liệu đăng nhập | users, quyền từ RBAC; quản trị /admin/users được kiểm tra backend |
| Test Groq thật | Đạt sau khi người dùng cho phép kết nối bên ngoài |

Kiểm thử formatter dùng Node.js với DOM tối thiểu có chặn innerHTML, không phải kiểm thử tương tác trình duyệt hoàn chỉnh. Chưa chụp giao diện mới trong trình duyệt thật. Logo JPG có nền caro sẵn; giữ nguyên ảnh người dùng cung cấp.

## Bộ 10 câu chuẩn

Đáp án dưới đây được tính lại trực tiếp từ bảng gốc và so sánh với truy vấn các view AI. Các câu SQL oracle nằm trong STANDARD_CASES của tests/test_chat_flow.py; không nhập tay đáp án.

| Câu hỏi | Đáp án tính bằng SQL gốc | So với truy vấn AI |
|---|---|---|
| SH 160i giá bao nhiêu? | 92.500.000 VNĐ; 96.500.000 VNĐ; 100.500.000 VNĐ | Đạt |
| Có bao nhiêu khách hàng đã mua xe? | 30 | Đạt |
| Tổng số đơn hàng? | 30 | Đạt |
| Tổng tồn kho toàn hệ thống? | 451 | Đạt |
| Mỗi phân khúc có bao nhiêu phiên bản? | Xe số, 7; Xe ga, 18; Xe côn tay, 3 | Đạt |
| Mẫu xe nào có giá niêm yết cao nhất? | SH 160i, SH 160i - Thể thao - Đỏ đen, 100.500.000 VNĐ | Đạt |
| Tổng doanh thu thuần của các đơn? | 1.359.600.000 VNĐ | Đạt |
| Bao nhiêu khách hàng chọn trả góp? | 42 | Đạt |
| Có bao nhiêu dòng tồn kho đang hết hàng? | 9 | Đạt |
| Vision 110 có bao nhiêu phiên bản? | 3 | Đạt |

## File thêm/sửa trong lần này

- Logo/giao diện: docs/images/logo.jpg (ảnh người dùng), static/images/logo.jpg, templates/base.html, templates/login.html, templates/index.html, static/portal.css.
- Chat/định dạng: static/chat-formatting.js, static/chat.js, text_formatting.py, app.py, ai_service.py, static/admin.js, static/records.js.
- Truy xuất và kiểm tra database: rag_service.py, check_db.py.
- Test: tests/chat_formatting_check.js, tests/test_chat_presentation.py.
- Tài liệu: README.md, docs/account_management.md, docs/test_results.md.

AGENTS.md đã có thay đổi của người dùng trước khi làm; giữ nguyên, không đưa vào commit triển khai. Không git push. Thông tin bí mật .env không xuất vào báo cáo hoặc commit.

---

﻿# Kết quả nghiệm thu Honda AI Portal M1–M6

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
# Cập nhật kết nối MySQL dùng chung - 14/10/2026

- `python -X utf8 init_db.py --extensions-only`: thành công, products=10, product_variants=28, inventory=84, customers=80, customer_profiles=80, orders=30.
- `python -X utf8 check_db.py`: thành công bằng tài khoản `admin_nt`, 89 tài khoản ứng dụng.
- `python -X utf8 scripts/configure_shared_mysql.py --network 192.168.10.0/24`: chạy hai lần thành công.
- Kết nối TCP tới `192.168.10.160:3306` ngay từ máy chủ: `admin_nt@192.168.10.0/255.255.255.0` đọc 30 đơn; `chatbot_ro@192.168.10.0/255.255.255.0` đọc 28 dòng view sản phẩm. Chưa thử từ máy thành viên.
- `python -X utf8 -m pytest -q --tb=short` với quyền truy cập mạng: **131 passed, 1 failed in 12.89s**. Lỗi `test_logo_and_formatter_served_locally`: ảnh `docs/images/logo.jpg` đã có thay đổi từ trước, khác ảnh `static/images/logo.jpg`. Không sửa ảnh hoặc assertion trong nhiệm vụ cấu hình MySQL.
- Lần chạy trong sandbox: 126 passed, 6 failed; 5 lỗi gọi Groq do socket bị chặn, chạy lại có mạng đã đạt cả 5.
- Không chạy reset vì nhiệm vụ hiện tại là đổi tài khoản và chia sẻ database đang có dữ liệu. Không khẳng định toàn bộ test đã đạt.
- Wi-Fi máy chủ là Public. Auto-review từ chối tạo quy tắc firewall mở TCP 3306 trên Private/Public cho LAN; chưa thay đổi firewall, cần chủ máy duyệt rõ phạm vi trước khi hoàn tất kết nối máy khác.
