# Kiểm chứng CSDL dùng chung LAN - 21/10/2026

Môi trường thật: Windows, Python 3.13, MariaDB 10.4.32. Các mục từ ngày 14/10/2026 trở xuống là lịch sử. Lần này sửa lỗi kết nối/dữ liệu giữa các máy, không thay schema chuẩn và không đưa mật khẩu vào source.

Nguyên nhân đã kiểm tra: `.env` dùng loopback nên mỗi máy có database riêng; IP máy chủ đã đổi từ mạng `192.168.10.0/24` sang `192.168.100.187/24` nhưng account LAN cũ chưa đổi. Khởi tạo trước đây bỏ qua cập nhật credential chatbot nếu migration 03 đã chạy. File dump cũ trong Git không có migration/view/routine, không dùng làm cơ chế đồng bộ.

| Kiểm chứng | Kết quả thật |
|---|---|
| `python init_db.py --reset` | Đạt; áp dụng 13 extension theo thứ tự 02–14; 11 mẫu, 31 phiên bản, 93 tồn kho, 80 hồ sơ khách, 30 đơn |
| `python -m pytest -q` qua `scripts/verify_with_snapshot.py` | **310 passed in 61.92s (0:01:01)** |
| Chạy không có API key: `test_ai.py`, `tests/test_groq_queries.py` | **5 skipped in 0.01s**; không gửi yêu cầu LLM |
| Extension 02, 03, 04 chạy trực tiếp 2 lần/file | Đạt; số lượng dữ liệu không đổi; khôi phục view bổ sung 05/07/13 sau kiểm tra |
| Đổi mật khẩu, chạy cấp account lặp lại, thu hồi quyền bảng gốc cấp nhầm | Đạt trên MySQL thật bằng account tạm; mật khẩu cũ bị từ chối 1045, quyền đọc bảng/ghi của chatbot bị từ chối 1142 |
| Đổi mật khẩu khi migration 03 đã được ghi nhận | Đạt; kết nối mới dùng mật khẩu mới thành công; test trả lại credential gốc |
| Guest và user 5 hỏi giá vốn, audit denied; sales user 3 đọc tồn; guest không thấy tài liệu sales | Đạt; bộ test quyền/backend hiện có |
| Validator chặn DROP, nhiều statement, bảng ngoài whitelist và truy vấn nguy hiểm | Đạt; giữ nguyên assertion |
| Truy vấn tổng tồn, đếm dòng hết hàng, bộ lọc trạng thái khách hàng và thống kê | Đạt đối chiếu SQL gốc; sửa tổng hợp sai và bộ lọc bị bỏ qua |
| Dữ liệu ADV trong test đồng bộ Excel/chat | Fixture tự tạo và dọn trên MySQL; không phụ thuộc dữ liệu được nhập riêng trên một máy |
| Xuất workbook | Chỉ xuất khách có hồ sơ; không trộn tài khoản demo thiếu hồ sơ; mỗi test giữ/khôi phục workbook |
| Khôi phục sau reset/test | Hash và số dòng **mọi bảng** khớp snapshot; database thực tế trở lại 31 đơn; workbook khớp byte trước lần chạy có bảo vệ |
| Kết nối TCP qua `192.168.100.187:3306` từ chính máy chủ | Đạt với account LAN riêng cho app/chatbot; máy chủ MySQL `THUONG`, đủ 13 migration, đọc 5 view và hàm scope; bảng `users` bị chặn với chatbot |
| Tạo firewall rule có giới hạn LAN | Chưa áp dụng được: Windows trả `Access is denied`, System Error 5; phiên hiện tại không có quyền Administrator |
| Kết nối từ máy thành viên khác | Chưa kiểm chứng được; cần chạy `python scripts/check_shared_mysql.py` từ máy đó với cùng IP máy chủ |

10 câu chuẩn dưới đây dùng `tests/test_chat_flow.py::STANDARD_CASES`: đáp án kỳ vọng được tính bằng SQL trên bảng gốc ở mỗi lần chạy, đối chiếu với truy vấn qua view và câu trả lời API; không nhập tay đáp án.

| Câu hỏi | SQL tính đáp án kỳ vọng | Kết quả |
|---|---|---|
| SH 160i giá bao nhiêu? | `SELECT pv.list_price FROM product_variants pv JOIN products p ON p.id=pv.product_id WHERE p.model_name=%s ORDER BY pv.list_price` | Đạt |
| Có bao nhiêu khách hàng đã mua xe? | `SELECT COUNT(*) FROM customer_profiles WHERE status=%s` | Đạt |
| Tổng số đơn hàng? | `SELECT COUNT(*) FROM orders` | Đạt |
| Tổng tồn kho toàn hệ thống? | `SELECT SUM(quantity) FROM inventory` | Đạt |
| Mỗi phân khúc có bao nhiêu phiên bản? | `SELECT p.segment,COUNT(*) FROM products p JOIN product_variants pv ON pv.product_id=p.id GROUP BY p.segment ORDER BY p.segment` | Đạt |
| Mẫu xe nào có giá niêm yết cao nhất? | `SELECT p.model_name,pv.variant_name,pv.list_price FROM products p JOIN product_variants pv ON pv.product_id=p.id ORDER BY pv.list_price DESC LIMIT 1` | Đạt |
| Tổng doanh thu thuần của các đơn? | `SELECT SUM(oi.quantity*oi.unit_price-o.discount_amount) FROM orders o JOIN order_items oi ON oi.order_id=o.id` | Đạt |
| Bao nhiêu khách hàng chọn trả góp? | `SELECT COUNT(*) FROM customer_profiles WHERE payment_preference=%s` | Đạt |
| Có bao nhiêu dòng tồn kho đang hết hàng? | `SELECT COUNT(*) FROM inventory WHERE quantity=0` | Đạt |
| Vision 110 có bao nhiêu phiên bản? | `SELECT COUNT(*) FROM products p JOIN product_variants pv ON pv.product_id=p.id WHERE p.model_name=%s` | Đạt |

Trích kết quả lệnh thực tế (script chạy reset và pytest, luôn restore trong `finally`):

```text
> python init_db.py --reset
Applied 02_ai_views.sql
Applied 03_chatbot_ro_user.sql
Applied 04_indexes.sql
Applied 05_ai_product_details.sql
Applied 06_auth_dynamic_rbac.sql
Applied 07_own_scope_views.sql
Applied 08_air_blade_125_seed.sql
Applied 09_document_uploads.sql
Applied 10_customer_input.sql
Applied 11_sales_invoices.sql
Applied 12_catalog_bookings.sql
Applied 13_ai_vehicle_releases.sql
Applied 14_chat_tools_stock_imports.sql
MySQL schema and seed completed.
products: 11 (expected 11)
product_variants: 31 (expected 31)
inventory: 93 (expected 93)
customers: 80 (expected 80)
customer_profiles: 80 (expected 80)
orders: 30 (expected 30)
> python -m pytest -q
310 passed in 61.92s (0:01:01)
Restoring verified snapshot...
RESTORE VERIFIED: all table contents match the pre-reset snapshot.
RESTORE VERIFIED: source/export workbook bytes restored.
```

File mới: `mysql_accounts.py`, `scripts/check_shared_mysql.py`, `tests/test_mysql_deployment.py`. File sửa: `init_db.py`, extension 02/07, `scripts/configure_shared_mysql.py`, `scripts/allow_mysql_lan.ps1`, `scripts/verify_with_snapshot.py`, `business_routes.py`, `query_plans.py`, `sql_service.py`, `excel_sync.py`, `tests/conftest.py`, hai test Excel/chat tồn kho, `pytest.ini`, `.env.example`, `README.md`, báo cáo này.

DDL hàm scope dùng DROP IF EXISTS + CREATE thay cho OR REPLACE FUNCTION, theo [cú pháp MySQL 8.0](https://dev.mysql.com/doc/refman/8.0/en/create-procedure.html). Đã chạy thật trên MariaDB; chưa có server MySQL 8 riêng để xác nhận toàn bộ hệ thống trên engine đó.

Lưu ý dữ liệu/file: `check_db.py` và workbook nguồn đã có thay đổi chưa commit trước phiên này, không đưa vào commit bản vá. Lần kiểm thử đầu dùng công cụ cũ đã tái ghi Excel nguồn; nội dung đã được tái xuất từ database gốc sau restore, không khẳng định giữ nguyên byte workbook trước lần chạy đầu. Các lần chạy sau giữ/khôi phục byte workbook, đồng thời xác nhận hash database. Không thể báo git status sạch khi còn thay đổi của người dùng; không xóa hoặc commit gộp chúng.

Để hoàn tất phía máy thành viên: đặt `DB_HOST=192.168.100.187`, dùng credential app/chatbot của máy chủ và chạy `python scripts/check_shared_mysql.py`, rồi khởi động lại backend. Máy chủ cần bật. Nếu cổng bị chặn, chạy PowerShell **Administrator** với lệnh firewall trong README. Các rule `mysqld` có sẵn được giữ nguyên; không khẳng định script đã giới hạn toàn bộ quyền mạng của những rule đó.

---

# Kiểm chứng logo, câu trả lời và tài khoản - 14/10/2026

## Bổ sung đồng bộ khách hàng, nhập nhanh và chứng từ bán hàng - 14/10/2026

Phần này ghi kết quả của lần nâng cấp mới nhất. Các kết quả bên dưới là lịch sử những lần kiểm chứng trước đó.

Đã thêm `customer_input.py`, `customer_input_routes.py`, `customer_chat.py`, `sales_routes.py`, `inventory_policy.py`; extension `10_customer_input.sql`, `11_sales_invoices.sql`; các trang/script nhập khách và đơn hàng, font Noto Sans cục bộ có giấy phép. Đã nối luồng vào `app.py`, trang tài liệu/chat, chỉnh bộ lập truy vấn, cảnh báo tồn kho, khởi tạo extension, dependency và README. Schema chuẩn không đổi.

| Kiểm chứng | Kết quả |
|---|---|
| Excel nguồn có 19 cột, 80 khách, 30 thông tin mua | Đạt ở chế độ đọc/xem trước: nhận diện cập nhật 80 hồ sơ và 30 đơn hiện có; không nhập lại dữ liệu nguồn |
| XLSX tải từ giao diện, chọn danh mục Thông tin / Danh sách khách hàng | Đạt; mẫu tải xuống đúng tên/thứ tự cột, điện thoại giữ kiểu chữ; file khách chưa được đưa vào RAG |
| Thêm mới, cập nhật theo mã/email, hiển thị trước/sau và xác nhận | Đạt; phiên bản cũ, hồ sơ thay đổi và xung đột bị chặn; xác nhận lại không tạo trùng |
| Thiếu trường, ngày sai, email/điện thoại/enum/model/SKU/giá tiền sai, dòng JSON lỗi, trùng trong lô | Đạt; cả lô không ghi khách hoặc đơn khi có lỗi |
| Customer/guest/kỹ thuật viên, người khác sở hữu nháp, chi nhánh khác, thu hồi quyền | Đạt; backend kiểm tra mỗi lần gọi, không dựa vào nút ẩn |
| Tạo khách từ chat và nhập nhanh khách mua xe | Đạt; thu thập trường còn thiếu, hỗ trợ nhãn Giá trị mua và nhập từng lượt; chỉ tạo sau xác nhận |
| Thông tin mua kèm khách | Đạt; tạo đơn pending, quantity=1, approved_by=NULL, không tự thanh toán/giao xe/giảm tồn kho |
| Kho sắp hết hàng / hết hàng | Đạt đối chiếu SQL thật: 1–4 / 0; kiểm tra biên 0, 1, 4, 5 và scope sales NT01 |
| PDF từ đơn thật | Đạt đọc lại bằng pdfplumber: tên tiếng Việt đủ dấu, mặt hàng, trạng thái, tiền theo order_items và giảm giá đã lưu |
| Đơn pending/approved và paid/delivered | Phiếu xác nhận / hóa đơn bán hàng mô phỏng tương ứng; không khẳng định đã thu tiền cho đơn pending |
| Chặn xuất PDF trái quyền, ngoài chi nhánh, đơn hủy, số tiền sai | Đạt; yêu cầu cả order:read và invoice:export, lấy giao phạm vi hai quyền; xuất thành công có audit |
| Edge headless 1440×900 và 390×844 | Đạt nhập form/chat/file, nhập nhanh, gợi ý giá, xác nhận, tải PDF và tìm đơn; không lỗi JavaScript/tràn ngang trang |
| Replay trực tiếp extension 10 và 11, mỗi file 2 lần | Đạt, không lỗi và không nhân đôi permission/menu |

API/trang mới và quyền:

| Tuyến | Quyền và giới hạn |
|---|---|
| `/customer-input`, `/api/customer-input`, `/api/customer-input/lookups`, `/api/customer-input/template` | customer:write; chi nhánh được cấp; nháp chỉ chủ sở hữu; nhập từ file còn cần document:manage và quyền danh mục |
| `/api/customer-input/<id>`, `/api/customer-input/<id>/commit` | Chủ nháp; kiểm tra lại scope; thao tác ghi cần CSRF, version và confirmed=true |
| `/orders`, `/api/orders` | order:read; all/branch/own theo cấu hình backend; phân trang tối đa 20 dòng |
| `/api/orders/<id>/invoice.pdf` | order:read + invoice:export; giao scope; không lộ dữ liệu đơn ngoài phạm vi |

Ảnh kiểm thử tại `.pytest_cache/customer-input-ui/category-1440.png` và `category-390.png`. Các khách/đơn thử dùng email riêng và được dọn sau test, không xóa khách/đơn nguồn. PDF tạo trong bộ nhớ, không lưu file chứa thông tin cá nhân trong static.

Lệnh khởi tạo dùng `python -X utf8 init_db.py --extensions-only`: thành công; giữ nguyên 11 products, 31 variants, 93 inventory, 80 customer_profiles và 30 orders sau dọn test. Không chạy `--reset` vì database dùng chung đã có tài liệu và dữ liệu nghiệp vụ cần giữ; thao tác reset sẽ xóa dữ liệu đó.

Kết quả thật lần cuối với MySQL, API LLM đã cấu hình và Playwright trong PYTHONPATH:

```text
python -X utf8 -m pytest -q --tb=short --basetemp=D:/Projects/thuc_tap/project_thuc_tap/.pytest_cache/sales-full-run2
FAILED tests/test_chat_presentation.py::test_logo_and_formatter_served_locally
1 failed, 239 passed in 35.60s
```

Lỗi duy nhất là ảnh `docs/images/logo.jpg` khác byte so với ảnh `/static/images/logo.jpg`, tồn tại trước lần nâng cấp này. Không xóa test, không nới assertion, không đổi ảnh nhận diện ngoài phạm vi yêu cầu. Vì vậy chưa thể báo toàn bộ bộ kiểm thử pass. Riêng kiểm thử mới khách hàng/tồn kho/bán hàng và trình duyệt đều đạt.

Giới hạn: mỗi dòng một lần mua, số lượng 1; đơn trùng cùng khách/chi nhánh/phiên bản/giá được nhận diện là đơn hiện có. Không suy đoán nhiều lần mua giống hệt nhau. Khách mới có portal chưa kích hoạt. Chưa có quy trình duyệt/thanh toán đơn trong chức năng mới. Chứng từ PDF mô phỏng, chưa tích hợp hóa đơn điện tử thuế và chưa lưu bản hóa đơn bất biến; tải lại phản ánh đơn tại thời điểm tải. Các thay đổi người dùng trong `phuong_phap_trien_khai_de_an/` và `ke_hoach/` được giữ nguyên, không đưa vào commit tính năng.

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

## Sửa hiểu câu hỏi và cắt nội dung chat - 14/10/2026

Nguyên nhân: “chi nhánh nào còn” chưa được nhận thành intent tồn kho; tin nhắn là flex item có thể co chiều cao trong khi `overflow:hidden` cắt nội dung. Giao diện còn ghi đè câu trả lời bằng tiêu đề chung khi có bảng. Kiểm tra trình duyệt cũng phát hiện pool MySQL 5 kết nối trả lỗi ngay khi dashboard tải nhiều API đồng thời.

Đã sửa nhận diện tồn kho và lượt hỏi tiếp, tách đủ các tên xe trong câu so sánh, giải thích khi mẫu xe thiếu dữ liệu, giữ nguyên dung tích được hỏi. Quyền vẫn được kiểm tra trước truy vấn. Tin nhắn giữ nguyên chiều cao; bảng rộng cuộn ngang, cột tên xe/phiên bản đứng trước; giữ lời giải thích và nguồn. Pool chờ tối đa 5 giây khi bận và khởi tạo dưới khóa để tránh tranh chấp giữa các thread.

| Kiểm tra thực tế | Kết quả |
|---|---|
| Các biến thể “SH 160 chi nhánh nào còn”, “AB160 đại lý nào còn”, “ở đâu còn xe”, “còn không” | Đạt, nhận intent tồn kho |
| Tồn kho SH 160i cho admin, sales và kỹ thuật viên | Đạt, đối chiếu trực tiếp JOIN inventory/branches/products/product_variants; lọc đúng chi nhánh |
| Guest hỏi chi nhánh còn AB 125 | Đạt, từ chối trước SQL và có audit denied |
| So sánh AB 125 và AB 160 | Đạt, báo thiếu AB 125, giá/phiên bản AB 160 đối chiếu SQL gốc, không tự thay tên xe |
| So sánh Vision 110 và Lead 125 | Đạt, đủ phiên bản của cả hai mẫu theo SQL gốc |
| Lượt tiếp “chi nhánh nào còn?” | Đạt, giữ mẫu SH 160i, chỉ thấy NT01 của sales |
| Pool MySQL đang dùng đủ 5 kết nối | Đạt, request chờ và tiếp tục khi kết nối được trả về |
| Edge headless 1440×900, 1280×600, 390×844; mỗi kích thước 6 lượt hỏi thật | Đạt, không ép thấp/cắt tin, đủ bảng, không tràn ngang trang, cuộn ngang được trên điện thoại, không lỗi JavaScript |

Kiểm tra cuối: đặt `PYTHONPATH` tới `.pytest_cache/browser_tools` (Playwright được cài tạm), chạy `python -X utf8 -m pytest -q --tb=short` với mạng cho Groq: **149 passed, 1 failed in 17.61s**, không skip test trình duyệt. Lỗi còn lại là `test_logo_and_formatter_served_locally`: `docs/images/logo.jpg` đã có thay đổi trước nhiệm vụ, khác `static/images/logo.jpg`. Không sửa ảnh hoặc assertion để che lỗi. Các file ảnh và `AGENTS.md` người dùng đã sửa được giữ nguyên.

Ảnh kiểm tra: `.pytest_cache/chat-layout/chat-1440x900.png`, `chat-1280x600.png`, `chat-390x844.png`. Đây là kiểm tra cục bộ trên MariaDB thật, không khẳng định đã kiểm chứng trên máy thành viên khác. Không reset database trong nhiệm vụ sửa chat/giao diện vì không thay schema hay seed.

## Bổ sung Air Blade 125 - 14/10/2026

Đã thêm `data/schema/extensions/08_air_blade_125_seed.sql`: 1 mẫu xe, thông số, 3 phiên bản, 9 dòng tồn kho; không sửa schema chuẩn, không xóa hoặc ghi đè dữ liệu nghiệp vụ. Tất cả giá, giá vốn, thông số và tồn kho bổ sung là **dữ liệu mô phỏng cho thử nghiệm**, không phải thông tin thương mại thực tế. Excel gốc được giữ nguyên; extension là nguồn của phần bổ sung.

| Phiên bản mô phỏng | Giá niêm yết (VNĐ) | Tổng tồn kho (xe) |
|---|---:|---:|
| Air Blade 125 - Tiêu chuẩn - Đỏ đen | 42.500.000 | 16 |
| Air Blade 125 - Đặc biệt - Đen | 44.500.000 | 6 |
| Air Blade 125 - Thể thao - Xám đen | 46.500.000 | 5 |

Tồn kho mô phỏng theo chi nhánh: NT01=15, NT02=7, CR01=5; tổng=27 xe, 9 dòng, gồm 2 dòng số lượng bằng 0 để kiểm tra câu hỏi “còn xe”.

Kết quả thật khi chạy `python -X utf8 init_db.py --extensions-only`:

```text
Applied 08_air_blade_125_seed.sql
MySQL schema and seed completed.
products: 11 (expected 11)
product_variants: 31 (expected 31)
inventory: 93 (expected 93)
customers: 80 (expected 80)
customer_profiles: 80 (expected 80)
orders: 30 (expected 30)
```

Chạy lại cùng lệnh: migration được bỏ qua, số lượng giữ nguyên. Test còn chạy trực tiếp file SQL hai lần, sau khi chủ động chỉnh một số lượng tồn kho, để xác nhận không trùng bản ghi và không ghi đè cập nhật. `python -X utf8 check_db.py` xác nhận cùng các số lượng trên và 89 tài khoản đang hoạt động.

| Kiểm thử | Kết quả |
|---|---|
| Mẫu AB 125, thông số và 3 phiên bản | Đạt |
| Guest hỏi giá AB 125, đối chiếu SQL gốc | Đạt, không lộ giá vốn |
| Admin/sales NT01/sales NT02 hỏi AB 125 chi nhánh nào còn | Đạt, chỉ trả lượng >0 và đúng phạm vi chi nhánh |
| So sánh AB 125 và AB 160 | Đạt, 6 phiên bản của 2 mẫu, giá đối chiếu SQL gốc, không còn báo thiếu AB 125 |
| Không có dữ liệu AB 150 | Đạt, giữ kiểm tra không bịa bằng mẫu còn thiếu; không xóa test âm tính |
| Chạy lại seed và bảo toàn số lượng đã cập nhật | Đạt |
| Edge ở 1440×900, 1280×600, 390×844; 8 lượt hỏi/kích thước | Đạt, gồm tồn kho AB 125 và bảng so sánh AB 125/160 |

Kiểm tra cuối, với Playwright tạm trong `PYTHONPATH` và quyền kết nối mạng cho Groq: `python -X utf8 -m pytest -q --tb=short` → **156 passed, 1 failed in 19.58s**. Lỗi duy nhất vẫn là `test_logo_and_formatter_served_locally`: ảnh nguồn khác ảnh được phục vụ, đã có trước nhiệm vụ này; không thay ảnh hoặc nới assertion để cho qua.

Không chạy `--reset` trên database dùng chung: nhiệm vụ là bổ sung dữ liệu, không xóa dữ liệu hiện tại. Extension sẽ được áp dụng tự động sau seed khi người dùng chủ động khởi tạo lại bằng `init_db.py`. Các số lượng kỳ vọng và test được cập nhật đúng bộ dữ liệu 11/31/93; số khách hàng/đơn hàng không thay đổi.

## Tải lên và trích xuất PDF/DOCX/XLSX - 14/10/2026

Đã triển khai `/documents` và các API danh sách/tải lên/chi tiết/file gốc/trích xuất lại/hiệu đính/xuất bản. Parser tạo schema chung version 1 gồm block văn bản/bảng, vị trí trang/cột/sheet, metadata, số lượng và cảnh báo. Migration `09_document_uploads.sql` chỉ thêm bảng staging, quyền và menu; không sửa schema chuẩn. File gốc nằm ngoài static và không vào Git.

Tài khoản admin quản lý toàn hệ thống, quản lý chi nhánh có scope branch. Mỗi API kiểm tra session, CSRF, quyền quản lý và quyền danh mục. Scope kiểm tra lại khi xem, tải gốc, sửa hoặc xuất bản; bản nháp chưa được RAG thấy. `kb_documents` chỉ được ghi sau khi title/category/branch/content hợp lệ, đã đối chiếu, phiên bản không bị thay đổi và không còn marker ô lỗi/công thức thiếu kết quả. Người dùng sửa chữ/ô trong bản nội dung và ghi chú đối chiếu; cảnh báo gốc vẫn được giữ.

| Hạng mục kiểm tra | Kết quả thực tế |
|---|---|
| Bộ mẫu 18 file có đáp án độc lập | Đã tạo tại `data/samples/documents/` |
| PDF văn bản/bảng có kẻ đường/hai cột; DOCX đoạn và bảng; XLSX nhiều sheet | Đạt, văn bản/bảng đối chiếu gold và thứ tự block |
| PDF scan mờ/lệch và PDF hỗn hợp | Đạt phát hiện thiếu lớp văn bản, yêu cầu nhập/đối chiếu, không tạo điểm OCR giả |
| File hỏng, mã hóa, rỗng, sai đuôi/nội dung, macro, ZIP nén bất thường, XML entity | Đạt phát hiện và báo lỗi; không ghi kho tri thức |
| PDF 80 trang, XLSX 2.001 dòng | Đạt trích xuất; PDF >200 trang và Excel >10.000 dòng bị từ chối rõ ràng |
| Excel công thức chưa có cache | Đạt đánh dấu ô thiếu; chưa sửa marker thì không được lưu/đưa vào kho tri thức |
| Thiếu title/category/content, vượt 10 MB/60.000 byte nội dung, thiếu xác nhận/CSRF, phiên bản cũ | Đạt chặn ghi |
| Guest/sales/technician/customer gọi API quản lý tài liệu | Đạt từ chối trước parser |
| Quản lý chi nhánh truy cập file của chi nhánh khác; danh mục bị thu hồi quyền | Đạt từ chối; RAG tài liệu chi nhánh chỉ mở cho người được cấp |
| Lỗi timeout, nơi lưu file và tên file có đường dẫn | Đạt báo lỗi rõ, không lộ đường dẫn riêng; trạng thái xử lý bỏ dở thử lại được sau 2 phút |
| Edge headless 1440×900 và 390×844 | Đạt upload → preview bảng → sửa → xác nhận → xuất bản; scan hiển thị thiếu 0% coverage, nút xuất bản khóa; không tràn ngang trang |

Migration: `python -X utf8 init_db.py --extensions-only` thành công và chạy lại bỏ qua file đã áp dụng; chạy trực tiếp `09_document_uploads.sql` hai lần cũng thành công. Số lượng nghiệp vụ giữ nguyên: 11 mẫu xe, 31 phiên bản, 93 tồn kho, 80 khách, 80 hồ sơ, 30 đơn. Không reset/xóa database dùng chung để làm nhiệm vụ tải tài liệu.

Kiểm thử cuối dùng MySQL thật, mạng cho Groq và Playwright tạm trong `PYTHONPATH`:

```text
python -X utf8 -m pytest -q --tb=short --basetemp=D:/Projects/thuc_tap/project_thuc_tap/.pytest_cache/document-suite-run3
1 failed, 200 passed in 27.13s
```

**44 test mới đạt**: parser 23, API 19, trình duyệt 2. Lỗi duy nhất còn lại là `test_logo_and_formatter_served_locally`, đã có trước: ảnh nguồn và ảnh static khác nhau. Không sửa ảnh hoặc assertion để che lỗi. Thư mục tạm nằm trong workspace do quyền thư mục Temp Windows khác giữa sandbox và lượt chạy có mạng.

`python scripts/report_document_accuracy.py` đo 18 mẫu, không có lỗi khác kỳ vọng. Các mẫu được đo chữ đạt recall/precision token 100%; các bảng có gold đạt khớp ô 100%. Chỉ là mẫu tổng hợp kiểm soát; các case scan, công thức/ô gộp hoặc lỗi không bị gán điểm 100%. Xem [báo cáo chi tiết](document_extraction_report.md) về cách đo và giới hạn.

Giới hạn: chưa có OCR tự động, hàng đợi nền hoặc giới hạn RAM cứng Windows; xử lý trong request bằng subprocess timeout 45 giây. Bố cục phức tạp, bảng không đường kẻ, chữ trong ảnh, Word textbox/footnote/ô gộp và cache công thức cần đối chiếu. Backend dùng chung database phải chia sẻ nơi lưu file gốc. Ảnh kiểm tra nằm tại `.pytest_cache/document-ui/documents-1440.png` và `documents-390.png`.

File thêm: `document_parser.py`, `document_service.py`, `document_routes.py`, extension 09, `templates/documents.html`, `static/documents.js`, 18 mẫu và manifest, 2 script tạo mẫu/đo chất lượng, `requirements-dev.txt`, `.gitattributes`, 3 module test, báo cáo trích xuất. File sửa: `app.py`, `requirements.txt`, `.gitignore`, `static/portal.css`, README và báo cáo test này. `.gitattributes` giữ file tài liệu ở chế độ binary để clone trên Windows không đổi LF/CRLF làm hỏng PDF. Các thao tác di chuyển/xóa tài liệu trong `phuong_phap_trien_khai_de_an/` và file mới trong `ke_hoach/` xuất hiện trong lúc thực hiện là thay đổi ngoài nhiệm vụ, được giữ nguyên và không đưa vào commit.

## Sửa 12 hạng mục điều hành — 15/10/2026

Kết quả cuối thay thế trạng thái lỗi logo ở báo cáo cũ phía trên. Kiểm thử trên MariaDB 10.4.32,
Python 3.13, pytest 8.4.1, Playwright 1.64.0 và Edge cài cục bộ. Dịch vụ LLM được gọi thật vì môi trường có API key.

| Hạng mục | Bằng chứng kiểm tra | Kết quả |
| --- | --- | --- |
| Thêm khách trong chat | Tách tên/email/điện thoại ngăn dấu phẩy ở cả hai thứ tự; giữ địa chỉ nhiều dấu phẩy; chỉ lưu sau xác nhận | Đạt |
| Mã SP và giá mua | DOM kiểm tra Mã SP đứng trước giá mua; chọn SP014 lấy giá từ SQL và hiển thị 56.500.000; vẫn sửa được giá | Đạt |
| Hỏi gần hết hàng giữa lúc nhập khách | Câu hỏi trong ảnh chạy SQL; so toàn bộ dòng với SQL gốc; bản nháp không đổi phiên bản/nội dung | Đạt |
| Phạm vi Nha Trang/Cam Ranh | Nha Trang gồm NT01/NT02, Cam Ranh CR01; user 3 chỉ thấy NT01; quantity 1–4 | Đạt |
| Tổng tồn kho đầy đủ | “Tổng tồn kho” trong API chat có đủ 93 tổ hợp phiên bản–chi nhánh, tổng bằng SQL độc lập | Đạt |
| Giao diện | Edge desktop 1440×1000 và mobile 390×844 trên dashboard, khách hàng, tồn kho, lịch, danh mục, quản trị; không tràn ngang/JS error | Đạt |
| Logo | Biểu trưng SVG riêng, tải cục bộ ở đăng nhập và portal; giữ tỉ lệ | Đạt |
| Thanh công cụ | Mục chưa triển khai không xuất hiện; gom quản trị truy cập; quyền backend vẫn chặn truy cập trực tiếp | Đạt |
| Lịch sửa chữa | Đặt lịch, chặn trùng/sai ngày/sai scope, xác nhận/hoàn tất/hủy, chặn phiên bản cũ; guest bị chặn và khách chỉ thao tác lịch của mình | Đạt |
| Mẫu xe/giá/đời | Tạo phiên bản sinh tồn kho 0 mọi chi nhánh; sửa giá, năm đời và trạng thái; chặn dữ liệu sai/ghi đè phiên bản cũ; giá đơn hàng cũ giữ nguyên | Đạt |
| AI đọc đời xe mới | Sau đổi đời/giá, hỏi giá mẫu đời 2024; đối chiếu năm, lifecycle và giá đã lưu | Đạt |
| Biểu đồ tổng quan | Chart.js cục bộ: đường/cột/vòng, số liệu thu gọn, tải lại; KPI/biểu đồ tiếp tục đối chiếu SQL theo scope | Đạt |
| Tài khoản–vai trò–quyền | Một mục sidebar, các tab phân quyền riêng; giữ test tạo/sửa/gán/gỡ/thu hồi/phạm vi/audit và bảo vệ quản trị cuối | Đạt |
| Thống kê khách hàng | Tổng và phân bố theo trạng thái tính toàn bộ tập đã lọc, không phụ thuộc size=1; chi nhánh ngoài scope trả 0 | Đạt |
| Extension 12/13 | Chạy trực tiếp hai lần; không đổi counts nghiệp vụ | Đạt |

Lệnh xác minh thực tế qua script sao lưu/khôi phục:

```text
python -X utf8 scripts/verify_with_snapshot.py --basetemp=C:/Users/nguye/AppData/Local/Temp/ai-portal-full04 --tb=short

> python init_db.py --reset
Applied 02_ai_views.sql
Applied 03_chatbot_ro_user.sql
Applied 04_indexes.sql
Applied 05_ai_product_details.sql
Applied 06_auth_dynamic_rbac.sql
Applied 07_own_scope_views.sql
Applied 08_air_blade_125_seed.sql
Applied 09_document_uploads.sql
Applied 10_customer_input.sql
Applied 11_sales_invoices.sql
Applied 12_catalog_bookings.sql
Applied 13_ai_vehicle_releases.sql
MySQL schema and seed completed.
products: 11 (expected 11)
product_variants: 31 (expected 31)
inventory: 93 (expected 93)
customers: 80 (expected 80)
customer_profiles: 80 (expected 80)
orders: 30 (expected 30)

> python -m pytest -q
263 passed in 43.37s
Restoring verified snapshot...
RESTORE VERIFIED: all table contents match the pre-reset snapshot.
```

Sau khôi phục, `python -X utf8 check_db.py` xác nhận 11 mẫu, 31 phiên bản, 93 dòng tồn,
81 khách, 81 hồ sơ, 31 đơn, 90 tài khoản (89 hoạt động). Đây là dữ liệu hiện tại của người dùng;
counts 80/30 phía trên chỉ là bộ seed trong cửa sổ kiểm thử. Không giữ bản reset đè lên dữ liệu đang dùng.

Chạy lại trực tiếp extension:

```text
EXTENSIONS_RERUN_OK 1
EXTENSIONS_RERUN_OK 2
BUSINESS_COUNTS_UNCHANGED
```

Các thất bại trung gian đã xử lý: sandbox chặn mạng LLM; thư mục tạm cũ có ACL khác;
máy thiếu Playwright; fixture Excel sinh từ nhãn UI mới không có alias cho tiêu đề cũ;
assertion định dạng tiền/501/logo không còn đúng yêu cầu mới; cú pháp chờ trình duyệt cần hàm thay vì eval chuỗi dưới CSP.
Không bỏ test, không nới lỏng assertion an toàn. Test cũ được cập nhật theo hành vi yêu cầu mới và bổ sung kiểm tra tương ứng.

Ảnh kiểm tra: `.pytest_cache/improvements/dashboard-1440.png`, `dashboard-390.png`,
`chat-1440.png`, `chat-390.png`; các module trình duyệt cũ vẫn sinh ảnh riêng.
Snapshot trong `.pytest_cache/before-reset-*.sql` có dữ liệu riêng tư, được Git bỏ qua.

File thêm: `operations_routes.py`, extensions 12/13, `templates/operations.html`,
`static/operations.js`, `static/images/brand-mark.svg`, `scripts/verify_with_snapshot.py`,
`tests/test_requested_improvements.py`, `tests/test_improvements_browser.py`.

File sửa: `app.py`, `customer_chat.py`, `customer_input.py`, `query_planner.py`,
`question_language.py`, `sql_service.py`, `answer_renderer.py`, `business_routes.py`, `security.py`;
JS `admin`, `chat`, `customer-input`, `dashboard`, `records`; `static/portal.css`;
templates `admin`, `base`, `dashboard`, `index`, `login`, `records`;
tests `test_chat_presentation`, `test_customer_input_browser`, `test_portal`, `test_sales_features`;
`README.md`, `docs/routes_permissions.md`, báo cáo này.

Giới hạn vận hành: chat giữ tối đa 100 dòng theo validator, thông báo giới hạn và xem tiếp ở trang tồn kho phân trang;
lịch chưa có phân công kỹ thuật viên, giới hạn công suất hay nhắc lịch SMS; phiên bản xe mới có giá vốn 0 cần
quy trình tài chính bổ sung. Báo giá/cơ hội vẫn chưa triển khai và đã được ẩn khỏi menu.
File tạm Excel `ke_hoach/~$Ke_Hoach_Thuc_Tap.xlsx` có sẵn được giữ nguyên ngoài commit.

Đã khởi động lại đúng tiến trình Flask cũ trên cổng 5000 để nạp mã mới:
`FLASK_RESTART_OK pid=5428 status=200 new_logo=True`. Truy cập lại `http://127.0.0.1:5000` và tải lại trang để nhận giao diện mới.

## Giao diện đỏ và logo do người dùng chỉ định — 15/10/2026

Theo chỉ dẫn mới nhất, giao diện đổi sang đỏ `#CC0000` kết hợp trắng/xám, dùng logo nguyên bản
`docs/images/logo.jpg` thay cho biểu trưng riêng trước đó. Thay đổi đồng bộ menu, nút, viền header,
khung chat, thanh thống kê, tab quản trị và bảng màu biểu đồ. Logo dùng `object-fit: contain`,
giữ nguyên tỉ lệ ở trang đăng nhập, desktop và mobile. Dòng “Dữ liệu mô phỏng” giữ nguyên.

| Kiểm tra | Kết quả |
| --- | --- |
| SHA-256 nguồn và `static/images/logo.jpg` | Trùng: `4AC9D09BAF98CB427BD01627EFCA1ADC50CF2F56760EA6DC5A4C2057CE1D1369` |
| Test logo | HTTP 200, MIME image/jpeg, byte khớp chính xác ảnh nguồn |
| Edge desktop/mobile | Logo tải đúng; màu chủ đạo #CC0000; không tràn ngang, không lỗi JS |
| Kiểm thử toàn bộ MySQL/LLM/Edge | 263 passed trong 45,31 giây |
| Khôi phục dữ liệu sau reset/test | Hash nội dung tất cả bảng khớp snapshot trước reset |

```text
python -X utf8 scripts/verify_with_snapshot.py --basetemp=C:/Users/nguye/AppData/Local/Temp/ai-portal-red01 --tb=short
> python init_db.py --reset
MySQL schema and seed completed.
products: 11 (expected 11)
product_variants: 31 (expected 31)
inventory: 93 (expected 93)
customers: 80 (expected 80)
customer_profiles: 80 (expected 80)
orders: 30 (expected 30)
> python -m pytest -q
263 passed in 45.31s
Restoring verified snapshot...
RESTORE VERIFIED: all table contents match the pre-reset snapshot.
```

File sửa: `static/portal.css`, `static/dashboard.js`, `static/images/logo.jpg`,
`templates/base.html`, `templates/login.html`, `tests/test_chat_presentation.py`,
`tests/test_improvements_browser.py`, `tests/test_requested_improvements.py`, `README.md`, báo cáo này.
Ảnh desktop/mobile được cập nhật trong `.pytest_cache/improvements/dashboard-1440.png` và `dashboard-390.png`.

## Nhập hàng, công cụ chatbot và đồng bộ khách từ file — 15/10/2026

| Kiểm tra | Kết quả thật |
| --- | --- |
| Reset MySQL, extension 02–14 | Thành công; seed 11 mẫu, 31 phiên bản, 93 dòng tồn kho, 80 khách, 30 đơn |
| Toàn bộ pytest trên MySQL/LLM/Edge | **290 passed in 55.46s** |
| Khôi phục dữ liệu sau reset/test | Hash nội dung mọi bảng khớp snapshot trước chạy |
| Nhập hàng qua chat/API | Cộng đúng nhiều mã SP, giới hạn chi nhánh, chặn trùng chứng từ/xác nhận; lỗi một mặt hàng rollback cả phiếu |
| Phân luồng người dùng | Phiên backend; khách/guest không dùng nghiệp vụ nội bộ; khách gán nhầm superadmin vẫn bị chặn; thu hồi quyền trước xác nhận bị từ chối |
| Công cụ chat | Danh mục xe, lịch, tài khoản/mật khẩu, vai trò/quyền, tài liệu, đơn/chứng từ qua registry cố định; bản nháp và xác nhận idempotent |
| Khách từ PDF/DOCX/XLSX | Ghi khách thật sau xác nhận; lịch sử và lọc danh sách theo lần nhập; thiếu cột không xóa trường hiện có; tài liệu đổi phiên bản bị chặn |
| Excel 580 dòng (test riêng) | Ghi 580 khách, không tạo đơn ngoài ý muốn, xác nhận lại không nhân đôi; tài khoản mới không có mật khẩu dùng chung |
| Giới hạn nhập | Cho 1.000 dòng, chặn 1.001 dòng; sửa giới hạn cũ 200 khiến file thực tế bị chặn |
| Edge desktop 1440/mobile 390 | Nhập hàng/chat, đính kèm DOCX → xác nhận → danh sách và lịch sử; không lỗi JavaScript/không tràn ngang |
| File thực tế #245 | Xem trước HTTP 201, bản nháp #427: 580 dòng hợp lệ, 81 cập nhật + 499 tạo mới, không lỗi. **Chưa xác nhận ghi khách/đơn** để người dùng kiểm tra nội dung trước. |

```text
python -X utf8 scripts/verify_with_snapshot.py --basetemp=C:/Users/nguye/AppData/Local/Temp/ai-portal-tools-final04 --tb=short --show-capture=no
> python init_db.py --reset
Applied 14_chat_tools_stock_imports.sql
MySQL schema and seed completed.
> python -m pytest -q
290 passed in 55.46s
Restoring verified snapshot...
RESTORE VERIFIED: all table contents match the pre-reset snapshot.
```

Extension 14 được áp dụng lặp hai lần trên CSDL đang dùng không lỗi; backfill lịch sử cũ chạy lặp không tạo bản ghi trùng. Giữ dữ liệu kinh doanh hiện có: 81 khách và 31 đơn; việc chuẩn bị bản nháp #427 chỉ thêm metadata xem trước, không ghi khách/đơn. Không tự nhập cả hai file #227 và #245 vì chúng là cùng nguồn 580 khách.

File thêm: `stock_service.py`, `stock_routes.py`, `appointment_service.py`, `chat_tools.py`, `chat_action_routes.py`, `customer_file_import.py`, `data/schema/extensions/14_chat_tools_stock_imports.sql`, `scripts/backfill_customer_imports.py`, `templates/stock_receipts.html`, `static/stock-receipts.js`, `static/appointments.js`, `tests/test_chat_tools_imports.py`, `tests/test_tools_browser.py`.

File sửa: `db.py`, `security.py`, `access_control.py`, `app.py`, `operations_routes.py`, `customer_chat.py`, `customer_input.py`, `customer_input_routes.py`, `document_routes.py`, `business_routes.py`, `init_db.py`; các giao diện `templates/{index,documents,operations,records}.html`, `static/{chat,customer-input,documents,records}.js`, `static/portal.css`; test `test_admin.py`, `test_customer_input_browser.py`, `test_document_uploads.py`, `test_requested_improvements.py`; `README.md`, báo cáo này.

Giới hạn: PDF ảnh quét chưa OCR; nghiệp vụ chưa triển khai (báo giá/cơ hội) không trở thành công cụ chat; phiếu nhập chưa hạch toán giá vốn/công nợ. Chat không chạy mã/SQL ghi tùy ý. Xác nhận file thực tế còn chờ người dùng xem trước vì có 81 hồ sơ được cập nhật. Giữ nguyên file tạm Excel của người dùng ngoài commit, không `git push`.


## Bổ sung hiệu ứng tương tác trang đăng nhập - 22/10/2026

Phạm vi chỉ gồm frontend: thêm static/login-effects.js, bổ sung CSS hiệu ứng trong static/portal.css và liên kết script trong `templates/login.html`. Không thay đổi backend, route, session, CSRF, xác thực, database, form hoặc hành vi nút đăng nhập/khách.

| Kiểm tra | Kết quả |
|---|---|
| Nền gradient, vật thể trang trí và parallax theo chuột | Đã bổ sung |
| Kéo-thả vật thể trang trí | Đã bổ sung; chỉ xử lý trên vùng trang trí, không chặn form |
| Hover/focus và hiệu ứng xuất hiện | Đã bổ sung |
| prefers-reduced-motion | Đã bổ sung |
| Không CDN/dependency mới | Đạt; dùng CSS và JavaScript nội bộ |
| `node --check static/login-effects.js` | Đạt |
| git diff --check | Đạt |
| Toàn bộ pytest | Chưa chạy lại trong lần thay đổi frontend này |

Các kết quả 200/263/290 test pass ở những mục phía trên là kết quả lịch sử của các lần kiểm chứng trước, không phải kết quả mới của mục này.

## AI Evaluation & Training Readiness (22/10/2026)

| Hạng mục | Kết quả |
|---|---|
| Dataset seed có ground truth | Đạt, 200 câu JSONL |
| Validate schema dataset | Đạt |
| Intent baseline | 200/200 |
| Route baseline | 200/200 |
| SQL plan safety shape | 200/200 |
| Pytest pipeline + chat understanding | 41 passed |

Đây là benchmark route/planner trên câu hỏi đã duyệt, không phải fine-tuning và không chứng minh số liệu nghiệp vụ cố định. Tập `evaluation` được tách khỏi `development`; muốn mở rộng lên 1.000+ câu cần bổ sung các lỗi thật sau mỗi vòng benchmark.
## AI Training Pilot (22/10/2026)

| Hạng mục | Kết quả |
|---|---|
| System audit | Đã ghi nhận trong `reports/ai_training/system_audit.md` |
| Dataset pilot | 150 câu, đủ trường ground truth |
| Split | Development 100 / Validation 25 / Test 25 |
| Offline preflight | 150/150 route và intent/plan shape đạt |
| Pytest pilot + benchmark | 43 passed |
| Groq/live SQL/RAG groundedness | NOT_RUN; cần API key và fixture/snapshot read-only |

## Phase 2 Real AI Evaluation (22/10/2026)

| Hạng mục | Kết quả thực tế |
|---|---|
| Smoke | 10 case, 7 SELECT thực tế, 3 preflight |
| Toàn bộ pilot | 150 case |
| SELECT qua `chatbot_ro` | 105 thực thi, 0 lỗi |
| SQL cần Groq/template | 0 BLOCKED ở planner deterministic; Groq vẫn chưa gọi |
| Groq request | 0; `GROQ_API_KEY` không có |
| Latency SELECT | Trung bình 2.51 ms, P95 6.39 ms |
| Flask E2E/RAG | BLOCKED vì chưa có database fixture cô lập |

Các báo cáo chi tiết nằm trong `reports/ai_training/real_*.md` và `failure_analysis.md`. Không ghi row values hoặc PII vào báo cáo.
## Phase 3 Real AI Evaluation & Integration (22/10/2026)

| Hạng mục | Kết quả |
|---|---|
| SQL SELECT thật qua `chatbot_ro` | 105/105, lỗi 0 |
| Per-case redacted records | 150 records |
| Groq LLM | BLOCKED, thiếu `GROQ_API_KEY` |
| RAG groundedness | BLOCKED, thiếu fixture tài liệu/session cô lập |
| Flask full E2E | BLOCKED, chưa có database fixture cô lập |
| Generalization route | 30/30 sau sửa root-cause; 26/30 baseline |
| Regression tests | 67 passed (routing + pilot + question upgrade) |

Phase 3 được đánh dấu **PARTIAL / BLOCKED**, không tuyên bố Real LLM accuracy hay fine-tuning.