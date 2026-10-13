# Chatbot Honda — Flask + MySQL/MariaDB

Ứng dụng tra cứu dữ liệu Honda bằng SQL có kiểm soát quyền và RAG từ `kb_documents`. Dữ liệu Honda đi kèm là **dữ liệu mô phỏng**, không phải bảng giá thị trường.

## Cài đặt trên Windows

Yêu cầu Python 3.13+, MySQL 8.0.16+ hoặc MariaDB (đã kiểm chứng MariaDB 10.4.32 của XAMPP).

```powershell
python -m pip install -r requirements.txt
```

Tạo `.env` theo `.env.example`, giữ bí mật trong file này:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=honda_chatbot
CHATBOT_RO_USER=chatbot_ro
CHATBOT_RO_PASSWORD=choose-your-local-password
FLASK_SECRET_KEY=choose-a-random-session-secret
APP_ENV=dev
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

Mật khẩu root rỗng chỉ áp dụng cho cấu hình XAMPP cục bộ hiện tại. `db.py` đọc `.env` từ thư mục dự án, không phụ thuộc thư mục chạy lệnh. Khóa Groq cần lấy từ tài khoản thật; không dùng khóa giả.

## Khởi tạo và chạy

```powershell
python init_db.py --create-if-missing
python app.py
```

Truy cập `http://127.0.0.1:5000`. Lệnh tạo mới chỉ chạy schema/seed khi `honda_chatbot` chưa tồn tại; khi database đã có, chỉ áp dụng extension. Không sửa schema chuẩn.

```powershell
python init_db.py --extensions-only
```

Lệnh trên áp dụng lại view, dictionary/registry, tài khoản chỉ đọc và index, giữ dữ liệu nghiệp vụ. `--reset` có chức năng xóa database; chỉ dùng khi chủ động muốn tái tạo bộ dữ liệu, không dùng cho dữ liệu cần giữ.

Trong `APP_ENV=dev`, nếu chưa có `GROQ_API_KEY`, `/chat` trả dữ liệu SQL/tài liệu thật và `engine=database`. Đây là chế độ tra cứu trực tiếp, chưa gọi LLM. Khi có khóa thật, hệ thống dùng model Groq đang cấu hình và trả `engine=groq`. Ngoài dev, thiếu hoặc lỗi dịch vụ AI trả HTTP 503. Câu bị từ chối và câu không có bằng chứng không gửi tới model.

Ví dụ kiểm tra:

```powershell
$body = @{ question = 'SH 160i giá bao nhiêu?' } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:5000/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Backend lấy user từ phiên đăng nhập. Chỉ dev cho phép header `X-Demo-User-Id`: user 1 admin, 3 sales NT01, 5 kỹ thuật NT01, 6 kế toán. Không có user là guest. Phiên hội thoại dùng cookie Flask đã ký; không nhận user id hoặc session id từ nội dung câu hỏi.

## Dữ liệu, quyền và giới hạn

- SQL dùng tài khoản `chatbot_ro@localhost`, chỉ SELECT năm view AI và EXECUTE hàm phạm vi chi nhánh. Không đọc bảng gốc, không ghi.
- Backend tính whitelist theo registry + quyền của từng user; kiểm tra intent trước truy xuất. SQL được kiểm tra bằng AST sqlglot, giới hạn 100 dòng.
- Các câu hỏi phổ biến dùng truy vấn tham số hóa trong `query_plans.py`. Pipeline hiện tại không gọi LLM để sinh SQL tùy ý.
- `schema_context.py` dựng schema theo whitelist từ metadata và `ai_data_dictionary`. View không hỗ trợ COMMENT riêng nên mô tả tiếng Việt được lưu bằng dictionary.
- Phạm vi chi nhánh đặt vào `@ai_branch`, view lọc qua `fn_session_branch()`; backend reset biến khi trả connection về pool.
- MariaDB dùng timeout `max_statement_time=5` giây, FULLTEXT thường và tìm RAG bằng LIKE có tham số. MySQL dùng `MAX_EXECUTION_TIME=5000` mili giây và FULLTEXT ngram. Chưa kiểm chứng nhánh MySQL 8 trên môi trường này.
- RAG chỉ đọc tập `v_user_kb_access` của user. Guest chỉ đọc public và tài liệu không gắn chi nhánh; câu trả lời giữ nguồn id + tiêu đề.
- Opportunity, Quote, Booking chưa có schema, các endpoint trả HTTP 501. Role customer chưa có quyền đọc đơn của chính mình; chưa tự cấp thêm quyền.

## Kiểm thử

```powershell
python -m pytest -q
```

Test MySQL dùng database thật; lỗi kết nối/schema là lỗi test, không tự skip. Test gọi Groq thật tự skip khi thiếu API key. Test prompt dùng client giả chỉ xác minh payload gửi tới model, không chứng minh chất lượng model thật. Mười câu chuẩn so sánh kết quả backend với SQL trực tiếp trên bảng gốc.

Kết quả thực tế: [docs/test_results.md](docs/test_results.md). Các kiểm tra API ghi thêm session, message và audit phục vụ kiểm chứng, không xóa dữ liệu nghiệp vụ.

Tài liệu dự án: [Báo cáo triển khai](docs/md/Bao_cao_Trien_khai_Chi_tiet.md), [Thiết kế luồng](docs/md/flow_design.md).
