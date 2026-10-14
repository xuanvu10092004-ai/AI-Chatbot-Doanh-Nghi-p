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

File thêm: `document_parser.py`, `document_service.py`, `document_routes.py`, extension 09, `templates/documents.html`, `static/documents.js`, 18 mẫu và manifest, 2 script tạo mẫu/đo chất lượng, `requirements-dev.txt`, 3 module test, báo cáo trích xuất. File sửa: `app.py`, `requirements.txt`, `.gitignore`, `static/portal.css`, README và báo cáo test này. Các thao tác di chuyển/xóa tài liệu trong `phuong_phap_trien_khai_de_an/` và file mới trong `ke_hoach/` xuất hiện trong lúc thực hiện là thay đổi ngoài nhiệm vụ, được giữ nguyên và không đưa vào commit.
