---
name: honda-mysql-rbac-migration
description: Quy trình từng bước để thay dữ liệu cũ bằng bộ dữ liệu Honda (honda_chatbot_rbac.sql, honda_import_data.sql, file Excel), chuyển ứng dụng Flask/Python từ SQLite sang MySQL, rồi làm CSDL "thân thiện với AI" (view v_ai_*, user chỉ-đọc, validator SQL, phân quyền RBAC trước khi truy xuất, RAG theo quyền) và kiểm thử. Dùng skill này mỗi khi người dùng nhắc tới chuyển SQLite sang MySQL, nạp dữ liệu Honda, RBAC cho chatbot, text-to-SQL an toàn, lọc tài liệu RAG theo quyền, hoặc dự án thực tập AI CRM, kể cả khi họ không nói rõ tên skill.
---

# Chuyển dự án sang MySQL + dữ liệu Honda + CSDL sẵn sàng cho AI

## Mục tiêu và định nghĩa "xong"

Dự án (thường ở `D:\Projects\thuc_tap\project_thuc_tap`) đang dùng SQLite với dữ liệu cũ. Nhiệm vụ gồm bốn việc theo thứ tự: (1) thay dữ liệu cũ bằng bộ dữ liệu Honda, (2) chuyển code sang MySQL, (3) thêm lớp CSDL cho AI truy xuất đúng và an toàn, (4) kiểm thử bằng CSDL thật.

Chỉ báo "xong" khi tất cả điều sau đúng và bạn đã TỰ chạy để thấy kết quả thật:
- Số dòng sau khi nạp khớp bảng ở `references/schema-and-data.md` mục 7.
- Chạy `init_db --reset` hai lần liên tiếp đều ra cùng kết quả.
- Không còn `sqlite`, `PRAGMA`, `AUTOINCREMENT`, file `*.db` trong code đang chạy.
- Toàn bộ test trong `references/test-plan.md` pass, kết quả ghi vào `docs/test_results.md`.
- `git status` sạch, mỗi giai đoạn một commit, chưa `git push`.

Đọc `references/schema-and-data.md` trước khi viết bất kỳ câu SQL hay code truy vấn nào. Đọc `references/test-plan.md` trước khi viết test.

## Quy tắc nền (kèm lý do)

1. **Không đoán, không bịa.** Thiếu file, thiếu `.env`, không kết nối được MySQL, schema không có bảng cần thiết: dừng và báo đúng chỗ thiếu. Lý do: dữ liệu và mật khẩu đoán sai gây hỏng thật, còn câu hỏi thì rẻ.
2. **`honda_chatbot_rbac.sql` là nguồn chuẩn, không sửa.** Sửa code cho khớp schema, không đổi tên bảng/cột. Mở rộng schema chỉ bằng file mới trong `data/schema/extensions/` đánh số, chạy lại được nhiều lần.
3. **Opportunity, Quote, Booking chưa có bảng.** Giữ nguyên module, đánh dấu `# TODO(schema-extension)`, endpoint trả HTTP 501 kèm thông báo rõ. Không tự thiết kế bảng. Lý do: người dùng sẽ cung cấp file mở rộng schema riêng, thiết kế tự phát sẽ xung đột.
4. **Bí mật nằm ở `.env`.** Không in mật khẩu, khóa API ra log, báo cáo hay commit. Có `.env.example` không chứa bí mật. `.env` nằm trong `.gitignore`.
5. **Mọi truy vấn tham số hóa.** Tên bảng/cột/`ORDER BY` động chỉ đi qua whitelist cố định. Lý do: tên không tham số hóa được, nên chỉ có whitelist mới chặn được tiêm SQL ở đó.
6. **Quyền kiểm tra ở backend, mặc định từ chối.** `user_id` lấy từ phiên đăng nhập của backend, không bao giờ lấy từ nội dung tin nhắn hay từ LLM. Chế độ dev (`APP_ENV=dev`) cho phép header `X-Demo-User-Id`. Không có user thì là guest.
7. **Không làm các việc phá hoại** ngoài phạm vi: `git push`, `git reset --hard`, `DROP DATABASE` khác `honda_chatbot`, xóa file không thuộc nhiệm vụ.
8. **Báo cáo trung thực.** Test fail thì sửa code, không xóa test, không nới assertion. Phần chưa kiểm chứng (ví dụ chưa chạy trên MySQL 8) phải nói rõ.

## Quy trình

Làm lần lượt. Mỗi giai đoạn có **cổng**: phải thỏa cổng mới sang giai đoạn sau. Nếu người dùng yêu cầu dừng sau mỗi giai đoạn để duyệt thì dừng; nếu không, báo cáo ngắn rồi đi tiếp.

### Giai đoạn 0: Khảo sát (chỉ đọc)
1. Xác định ngôn ngữ, framework, driver (ví dụ Flask + `sqlite3` trực tiếp).
2. Liệt kê mọi chỗ phụ thuộc SQLite: `sqlite3`, `*.db`, `PRAGMA`, `AUTOINCREMENT`, `INSERT OR REPLACE`, `date('now')`, `datetime('now')`, placeholder `?`, migrations, seed, test, README, Dockerfile.
3. Kiểm tra 4 file Honda có trong workspace không (`data/new_honda/` hoặc `data/`).
4. Lập bảng ánh xạ bảng cũ sang bảng Honda: `customers` thành `users` + `customer_profiles`; `inventory` thành `inventory` + `product_variants` + `products`; `documents` thành `kb_documents` + `kb_categories`; `chat_logs` thành `chat_sessions` + `chat_messages` + `chatbot_audit_log`; `quotes` gần với `orders` + `order_items` nhưng không 1-1; `opportunities`, `bookings`, `customers.company` không có tương đương.
5. **Cổng:** trình bày kết quả và danh sách thay đổi dự kiến. Chưa sửa gì.

### Giai đoạn 1: Sao lưu rồi thay dữ liệu cũ
1. Tạo branch riêng (ví dụ `feature/migrate-mysql-honda-data`). Thư mục `data/` có thể đang untracked, nên `git add data/` cùng file Excel cũ rồi commit sao lưu TRƯỚC khi di chuyển hoặc xóa gì. Ghi lại hash commit sao lưu.
2. Sắp xếp: `data/schema/honda_chatbot_rbac.sql`, `data/seed/honda_import_data.sql`, `data/source/honda_dataset_khach_hang_san_pham.xlsx`, `data/tools/import_excel_to_sql.py`, `data/schema/extensions/`. Hai bản trùng tên: so sánh, báo chỗ khác, dùng bản trong `new_honda`.
3. Xóa dữ liệu cũ: file `*.db`/`*.sqlite`, Excel cũ (`git rm`), script/schema SQLite cũ. Không xóa code service, test, `.git`.
4. **Cổng:** liệt kê chính xác file đã di chuyển/xóa; `git status` sạch sau commit.

### Giai đoạn 2: Nạp MySQL thật và chuyển code
1. Kiểm tra `.env` có đủ `DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME` và `mysql --version` từ 8.0.16. Thiếu thì dừng.
2. Viết lại `init_db.py`: chạy schema rồi seed rồi các file trong `extensions/` theo thứ tự số. Bắt buộc cờ `--reset` và chỉ chạy khi `DB_NAME == "honda_chatbot"`, vì schema có `DROP DATABASE`. Cách chạy file SQL: gọi `mysql` CLI bằng `subprocess` với `--default-character-set=utf8mb4` và đẩy file qua stdin, hoặc dùng `sqlparse.split`. KHÔNG dùng `split(';')` vì nội dung `kb_documents` có dấu `;` trong chuỗi.
3. Tạo `requirements.txt` (ghim phiên bản) gồm driver MySQL (`PyMySQL` hoặc `mysql-connector-python`), `sqlglot`, `pytest`, `python-dotenv`.
4. Tạo module kết nối tập trung (pool, `utf8mb4`, đọc `.env`). `database_service.py`, `sql_service.py`, `rag_service.py` chỉ lấy kết nối từ đó.
5. Chuyển code: placeholder `?` thành `%s`; `date('now')` thành `CURDATE()`; `datetime('now')` thành `NOW()`; `INSERT OR REPLACE` thành `INSERT ... ON DUPLICATE KEY UPDATE`; bỏ `PRAGMA`; `LIMIT {x}` thành tham số; tên bảng/`ORDER BY` thành whitelist. Chuyển các phần có ánh xạ rõ; phần còn lại theo quy tắc nền số 3.
6. **Cổng:** chạy `init_db --reset` thật, dán số dòng thực tế và so với kỳ vọng; chạy lần hai, số không đổi; khởi động Flask với MySQL và gọi thử endpoint khách hàng, kho, dashboard, chat. Lệch số thì dừng.

### Giai đoạn 3: Lớp CSDL cho AI
Mọi thứ ở đây chỉ THÊM mới.

1. **View cho AI.** Sao chép `assets/02_ai_views.sql` vào `data/schema/extensions/`. File đã kiểm chứng chạy được hai lần liên tiếp. Nó tạo `v_ai_products`, `v_ai_inventory`, `v_ai_customers`, `v_ai_orders`, `v_ai_product_costs` (không có `password_hash`; giá vốn tách riêng), hàm `fn_session_branch()`, bảng `ai_view_registry` (view nào cần permission nào) và `ai_data_dictionary` (mô tả tiếng Việt).
2. **User chỉ-đọc `chatbot_ro`.** Viết script Python (không viết mật khẩu vào file SQL): lấy `CHATBOT_RO_PASSWORD` từ `.env`, `CREATE USER IF NOT EXISTS`, rồi `GRANT SELECT` trên từng view trong `ai_view_registry` và `GRANT EXECUTE` trên `fn_session_branch`. Kết nối của text-to-SQL PHẢI dùng user này. Đã kiểm chứng: user này đọc được view, bị chặn khi đọc bảng gốc và khi ghi.
3. **Luồng cho mỗi câu hỏi của người dùng**, theo đúng thứ tự:
   1. Xác định user từ phiên (không có thì guest).
   2. Phân loại intent, tra `chatbot_intents`, kiểm tra permission qua `v_user_permissions` (guest: qua role `guest` trong `role_permissions`).
   3. Bị từ chối: ghi `chatbot_audit_log` (denied + lý do), trả lời chung chung, không xác nhận dữ liệu có tồn tại.
   4. Tính `allowed_views` = các view trong `ai_view_registry` có permission mà user có. Tập này do backend tính, không bao giờ lấy từ LLM.
   5. Dựng ngữ cảnh schema cho prompt CHỈ từ `allowed_views`: cột từ `information_schema` và mô tả từ `ai_data_dictionary`, kèm từ điển đồng nghĩa ("xe ga" = `tay_ga`, "xe số" = `xe_so`, "xe côn" = `con_tay`, "đại lý/cửa hàng/chi nhánh" = `branches` với mã NT01, NT02, CR01, tiền tệ VNĐ).
   6. LLM sinh SQL, rồi `assets/sql_guard.py::validate_sql(sql, allowed_views)`. Sao chép file này vào mã nguồn; đã thử 5 ca hợp lệ và 14 ca độc hại.
   7. Thực thi bằng kết nối `chatbot_ro`: `SET @ai_branch = <branch_id hoặc NULL>`, đặt timeout, chạy, và LUÔN reset `@ai_branch = NULL` trong khối `finally`. Lý do: connection pool dùng lại kết nối, không reset thì phạm vi chi nhánh của user này rò sang user khác.
   8. Trả lời chỉ dựa trên các dòng kết quả. Ghi `chat_sessions`, `chat_messages`, `chatbot_audit_log` (allowed).
4. **Phạm vi chi nhánh:** lấy từ `user_roles.scope_branch_id` của role cấp permission đó. Nếu có role không giới hạn thì `NULL`. Nếu user bị giới hạn ở nhiều chi nhánh khác nhau thì từ chối và báo lý do (`@ai_branch` chỉ nhận một giá trị).
5. **Timeout:** MySQL dùng `SET SESSION MAX_EXECUTION_TIME = 5000` (mili-giây, chỉ áp cho SELECT); MariaDB dùng `SET SESSION max_statement_time = 5`. Nhận biết bằng `SELECT VERSION()`.
6. **RAG:** chỉ truy xuất trong `v_user_kb_access` của user; guest chỉ thấy danh mục public và tài liệu `branch_id IS NULL`. Trả lời kèm nguồn (id và tiêu đề tài liệu). Không có bằng chứng thì nói rõ là không có, không bịa. FULLTEXT với `WITH PARSER ngram` là tính năng riêng của MySQL (MariaDB không có): thêm trong file extension `04_indexes.sql` cùng index cho `orders(customer_id)`, `orders(branch_id, status)`; nếu môi trường không hỗ trợ thì dùng `LIKE` làm phương án dự phòng và ghi chú rõ.
7. **Tra cứu đơn của chính khách hàng:** không đi qua text-to-SQL. Dùng truy vấn tham số hóa cố định `WHERE customer_id = %s` với id của phiên. Role `customer` hiện không có `order:read`; hỏi người dùng có muốn thêm permission `order:read_own` không, không tự thêm.
8. **Cổng:** `init_db --reset` chạy cả các file extension hai lần liên tiếp không lỗi; `chatbot_ro` được tạo; validator chạy đúng.

### Giai đoạn 4: Kiểm thử và hồ sơ
1. Viết `pytest` theo `references/test-plan.md` (A đến G), dùng MySQL thật. Đáp án kỳ vọng tính bằng SQL lúc chạy test, không gõ tay.
2. Chạy `python -m pytest -q` và dán kết quả thật. Test gọi API LLM tự skip khi không có khóa.
3. Ghi `docs/test_results.md` (bảng đạt/không đạt, số thực tế) và cập nhật README: yêu cầu MySQL 8.0.16+, cách tạo `.env`, lệnh chạy trên Windows PowerShell.
4. Rà soát: `grep` không còn dấu vết SQLite; không có SQL nối chuỗi từ dữ liệu người dùng; không có bí mật trong git.
5. **Cổng:** mục "Định nghĩa xong" ở đầu file đều đúng.

## Khi nào dừng và hỏi người dùng

| Tình huống | Hành động |
|---|---|
| Thiếu file Honda, `.env`, hoặc MySQL không kết nối được | Dừng, nêu đúng thứ thiếu. Không tạo tài khoản, không đoán mật khẩu |
| Cần bảng cho Opportunity, Quote, Booking, hoặc cột `company` | Giữ TODO + HTTP 501, không thiết kế bảng |
| Số dòng sau khi nạp lệch kỳ vọng | Dừng, báo số thực tế và kỳ vọng |
| Hai bản trùng tên khác nhau | Báo chỗ khác, dùng bản mới, chờ nếu khác lớn |
| Thiếu permission cho một luồng (ví dụ khách xem đơn của mình) | Nêu vấn đề và lựa chọn, không tự thêm |
| Muốn sửa `honda_chatbot_rbac.sql` | Nêu lý do và hỏi trước |
| Test fail không rõ nguyên nhân sau hai lần thử sửa | Dừng, báo đã thử gì |

## Cạm bẫy đã gặp (đã kiểm chứng)

- **View không có COMMENT.** MySQL và MariaDB không cho `COMMENT` trên view hoặc cột của view. Mô tả tiếng Việt phải nằm trong `ai_data_dictionary`. Đừng thử `ALTER VIEW ... COMMENT`.
- **View không dùng được biến người dùng** (`@x`, lỗi 1351). Vì vậy phạm vi chi nhánh đi qua hàm `fn_session_branch()`.
- **Dấu `;` trong chuỗi** của `kb_documents`: đừng tách file SQL bằng `split(';')`.
- **PowerShell không hỗ trợ `<`:** dùng `mysql -e "source D:/duong/dan/file.sql"` (dấu `/`) hoặc subprocess.
- **Số điện thoại mất số 0 đầu** khi pandas đọc thành số: đọc cột đó với `dtype=str`.
- **`engine_cc` là SMALLINT:** 109,2 bị làm tròn thành 109.
- **`DROP DATABASE honda_chatbot`** nằm trong file schema: luôn có cờ `--reset` và kiểm tra tên DB.
- **Khác biệt MySQL và MariaDB:** FULLTEXT `ngram` và hint `MAX_EXECUTION_TIME` chỉ có ở MySQL. Mọi thứ trong skill này đã được chạy trên MariaDB 10.11; phải chạy lại cổng ở Giai đoạn 2 và 3 trên MySQL 8 thật.
- **Pool kết nối:** `@ai_branch` là biến phiên, phải reset sau mỗi truy vấn.
- **User mẫu id 8, 9** không có hồ sơ khách nên không thuộc `v_ai_customers`: không phải lỗi.
- **Số liệu đáp án chuẩn phụ thuộc file Excel.** Sinh lại Excel thì số đổi; tính đáp án bằng SQL trong test.

## Mẫu báo cáo sau mỗi giai đoạn

```
## Báo cáo Giai đoạn N
**Đã làm:** (ngắn gọn)
**File thay đổi:** thêm / sửa / xóa (liệt kê chính xác)
**Kiểm chứng thật:** lệnh đã chạy + kết quả dán nguyên văn (số dòng, kết quả test)
**Chưa làm được / rủi ro:** (nêu rõ và lý do)
**Commit:** hash + message
**Câu hỏi cho người dùng:** (nếu có, tối đa vài câu)
```

## Tài nguyên đi kèm

- `references/schema-and-data.md`: bảng, mã định danh, ma trận role-permission, intent, tài liệu tri thức, số dòng kỳ vọng.
- `references/test-plan.md`: các ca kiểm thử A đến G và 12 câu hỏi chuẩn với đáp án đối chiếu.
- `assets/02_ai_views.sql`: view AI, hàm phạm vi chi nhánh, registry và từ điển dữ liệu (đã chạy được trên MariaDB 10.11).
- `assets/sql_guard.py`: validator SQL dựa trên `sqlglot` (đã thử 5 ca hợp lệ, 14 ca bị chặn).
