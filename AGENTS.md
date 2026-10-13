Đọc `AGENTS.md` trước. Sau đó thực hiện nhiệm vụ dưới đây trên branch hiện tại.

# MỤC TIÊU
Làm CSDL MySQL "thân thiện với AI" để chatbot (text-to-SQL và RAG) truy xuất đúng, an toàn, có kiểm soát quyền. Chỉ THÊM mới (view, index, user MySQL, module Python, test), không sửa schema chuẩn.

# BỐI CẢNH
Dữ liệu Honda đã nạp vào MySQL (products=10, product_variants=28, inventory=84, khách hàng users id>100 = 80, customer_profiles=80, orders=30). Code đã chuyển sang MySQL. Các bảng quyền: roles, permissions, user_roles, role_permissions, view v_user_permissions, v_user_kb_access, bảng chatbot_intents, chatbot_audit_log, kb_categories, kb_documents, chat_sessions, chat_messages.

# VIỆC CẦN LÀM

1. LỚP VIEW CHO AI: tạo `data/schema/extensions/02_ai_views.sql` gồm các view chỉ-đọc `v_ai_products` (mẫu xe, phiên bản, màu, phân khúc, cc, giá niêm yết, tồn kho toàn hệ thống, KHÔNG có cost_price), `v_ai_inventory` (theo chi nhánh), `v_ai_customers` (KHÔNG có password_hash), `v_ai_orders` (kèm tên khách, tên xe, chi nhánh), `v_ai_product_costs` (giá vốn, chỉ dùng khi user có quyền `price:cost:read`). Thêm `COMMENT` tiếng Việt cho view và cột (ý nghĩa, đơn vị VNĐ, giá trị enum như `xe_so`/`tay_ga`/`con_tay`).

2. SCHEMA CONTEXT CHO PROMPT: viết module tạo mô tả schema từ `information_schema` + COMMENT, chỉ gồm các view `v_ai_*`, để đưa vào prompt text-to-SQL. Thêm từ điển đồng nghĩa: "xe ga" = tay_ga, "xe số" = xe_so, "xe côn" = con_tay, "đại lý/cửa hàng/chi nhánh" = branches (NT01, NT02, CR01), tiền tệ VNĐ.

3. AN TOÀN TRUY VẤN:
   - File `data/schema/extensions/03_chatbot_ro_user.sql`: tạo user MySQL `chatbot_ro` chỉ có SELECT trên các view `v_ai_*`. Mật khẩu lấy từ `CHATBOT_RO_PASSWORD` trong `.env` (script Python áp dụng, không viết mật khẩu vào file SQL). Kết nối của text-to-SQL phải dùng user này.
   - Validator SQL do LLM sinh: đúng 1 câu lệnh, chỉ SELECT, chỉ truy cập view whitelist, chặn `;` chen giữa, comment, `INTO OUTFILE`, `SLEEP`; tự thêm `LIMIT` tối đa 100 và đặt timeout (`MAX_EXECUTION_TIME`).

4. PHÂN QUYỀN TRƯỚC KHI TRUY XUẤT: dùng `chatbot_intents` + `v_user_permissions` để xác định intent và kiểm tra quyền TRƯỚC khi chạy SQL hoặc lấy tài liệu. Bị từ chối thì trả lời chung chung (không xác nhận dữ liệu có tồn tại) và ghi `chatbot_audit_log` (allowed/denied + lý do). `user_id` lấy từ phiên đăng nhập của backend; ở chế độ dev (`APP_ENV=dev`) cho phép header `X-Demo-User-Id`. Không có user thì coi là guest. Nếu user chỉ có quyền trong một chi nhánh (`scope_branch_id`) thì lọc theo chi nhánh đó.

5. RAG: file `data/schema/extensions/04_indexes.sql` thêm FULLTEXT index (`WITH PARSER ngram`) cho `kb_documents(title, content)` và index cho `orders(customer_id)`, `orders(branch_id, status)`. Truy xuất tài liệu CHỈ trong tập `v_user_kb_access` của user (guest chỉ thấy danh mục public). Câu trả lời kèm nguồn (id + tiêu đề tài liệu); không tìm thấy bằng chứng thì nói rõ, không bịa. Ghi `chat_sessions` và `chat_messages` cho mỗi lượt hỏi.

6. KIỂM THỬ (pytest, dùng MySQL thật):
   - Quyền: guest hỏi giá vốn thì bị từ chối và có dòng audit `denied`; sales (user 3) hỏi tồn kho thì được; kỹ thuật viên (user 5) hỏi giá vốn thì bị từ chối; guest không đọc được tài liệu danh mục sales.
   - Validator: `DROP TABLE`, nhiều câu lệnh, truy cập bảng ngoài whitelist đều bị chặn.
   - Bộ câu hỏi chuẩn: ít nhất 10 câu tiếng Việt với đáp án kỳ vọng tính trực tiếp bằng SQL (không hardcode tay), ví dụ giá niêm yết các phiên bản SH 160i (92.500.000 / 96.500.000 / 100.500.000), số khách "Đã mua" (30), tổng số đơn (30). Ghi bảng kết quả đạt/không đạt vào `docs/test_results.md`.
   - Test gọi API LLM phải tự skip khi không có API key.

7. Cập nhật `init_db.py` để chạy thêm các file trong `data/schema/extensions/` theo thứ tự số, và cập nhật README (phần cài đặt, `.env`, cách chạy test).

# KIỂM CHỨNG TRƯỚC KHI BÁO XONG
Tự chạy và dán kết quả thật: `python init_db.py --reset`, `python -m pytest -q`. Nếu có test fail thì sửa code (không xóa test, không nới lỏng assertion để cho qua). Nếu không kết nối được MySQL hoặc thiếu `.env`, dừng và báo rõ lỗi, đừng đoán mật khẩu.

# HOÀN THÀNH KHI
- 3 file extension (02, 03, 04) chạy lại nhiều lần không lỗi.
- Toàn bộ test pass, bảng kết quả trong `docs/test_results.md`.
- Không còn câu SQL nối chuỗi từ dữ liệu người dùng.
- `git status` sạch, mỗi hạng mục một commit.

# BÁO CÁO CUỐI
Danh sách file thêm/sửa, kết quả test thật, phần nào chưa làm được và vì sao. Không `git push`.