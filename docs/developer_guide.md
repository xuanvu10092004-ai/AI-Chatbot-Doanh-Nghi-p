# Hướng dẫn luồng chạy và cấu trúc mã nguồn

Tài liệu này mô tả các module Python do dự án tự viết ở thư mục gốc. Các thư
viện trong `external/`, `static/vendor/` và dữ liệu trong `data/` không phải
module ứng dụng nên không được liệt kê như mã nghiệp vụ.

## Chạy ứng dụng từ đầu

1. Cài dependencies, cấu hình `.env`, rồi chạy `python init_db.py
   --create-if-missing` để tạo/cập nhật schema và dữ liệu mẫu.
2. `python app.py` khởi tạo Flask. `app.py` đọc khóa phiên, đặt giới hạn request,
   đăng ký hook xác thực và nối các nhóm route.
3. Với mỗi HTTP request, `security.initialize_request` đọc session phía server,
   nạp user/role vào `g`, rồi route được gọi. Decorator quyền ở backend quyết
   định request có được chạy hay không; ẩn nút trên giao diện không thay thế
   bước kiểm tra này.
4. Route nhận/kiểm tra dữ liệu đầu vào, gọi service nghiệp vụ; service dùng
   `db.cursor()`/`db.transaction()` để truy cập MySQL. Route trả HTML hoặc JSON.
5. `static/*.js` gọi API và cập nhật giao diện. Không nên đưa kiểm soát quyền
   hoặc danh tính người dùng về phía trình duyệt.

## Các luồng người dùng chính

### Đăng nhập và phân quyền

`auth_routes.register_auth` đăng ký `/login`, `/guest`, `/logout` và
`/change-password`. Đăng nhập gọi `security.authenticate`; Flask lưu thông tin
đăng nhập trong session cookie được ký bằng `FLASK_SECRET_KEY`. Mỗi request,
`initialize_request` xác thực session rồi dựng `g.user`/vai trò;
`permissions` và `require_permission` kiểm tra quyền ở từng route.
`admin_routes` tiếp nhận yêu cầu quản trị, còn `admin_service` thực hiện kiểm
tra phạm vi, transaction và audit khi thay đổi dữ liệu/quyền.

### Chat dùng SQL hoặc RAG

`app.chat` kiểm tra câu hỏi đầu vào, khôi phục/tạo session chat, rồi chuyển
câu hỏi qua `routing.route_question`. Câu hỏi dữ liệu có cấu trúc đi tới
`sql_service.answer_sql_question`: planner chọn truy vấn, `sql_safety`/
`sql_guard` kiểm tra giới hạn an toàn, database trả bằng chứng; câu trả lời
được dựng bởi `answer_renderer` và có thể được diễn đạt bởi `ai_service`.
Câu hỏi tài liệu đi tới `rag_service.search_documents`, nơi nguồn phải được
lọc theo quyền. `access_control` quản lý session, lịch sử, intent và quyền
truy xuất. Kết quả sau đó được ghi lại và trả về giao diện.

### Tải tài liệu và nhập danh sách khách

1. `document_routes` nhận file và kiểm tra loại/quyền/kích thước request.
2. `document_service` lưu file và metadata; `document_parser` trích xuất PDF,
   DOCX hoặc XLSX thành các khối văn bản/bảng.
3. Từ màn nhập khách hoặc chat, request gọi
   `customer_input_routes`/`chat_action_routes`, rồi tới
   `customer_file_import.stage_document`.
4. `stage_document` kiểm tra nhân viên, quyền, danh mục và phiên bản tài liệu;
   `extracted_rows` ánh xạ header, kiểm tra cấu trúc, chuẩn hóa và tạo bản nháp.
   Bước này **chưa ghi thay đổi khách hàng chính thức**.
5. Người dùng xem và hiệu đính bản nháp qua `customer_input.revise`; chỉ khi
   xác nhận mới gọi `customer_input.commit`. `excel_sync` đồng bộ workbook sau
   commit thành công.

### Các chức năng nghiệp vụ khác

Các nhóm `business_routes`, `sales_routes`, `operations_routes`,
`stock_routes`, `dashboard_routes` tiếp nhận API theo từng nghiệp vụ; phần
truy vấn hoặc quy tắc dùng chung thường đặt trong service tương ứng như
`dashboard_service`, `appointment_service`, `stock_service` và
`database_service`. `chat_tools` đưa một số thao tác nghiệp vụ vào giao diện
chat, nhưng vẫn phải lọc công cụ và kiểm tra quyền trước khi thực hiện.

## Tra cứu nhanh module Python

### Khởi động, đăng nhập và kiểm soát quyền

| File | Vai trò |
|---|---|
| `app.py` | Điểm khởi chạy Flask; cấu hình session, hook request, đăng ký routes và endpoint chat. |
| `auth_routes.py` | Endpoint đăng nhập, guest, đăng xuất và đổi mật khẩu. |
| `security.py` | Xác thực tài khoản, nạp danh tính/quyền, decorator kiểm tra quyền, CSRF và audit. |
| `access_control.py` | Intent/quyền chatbot, tạo hoặc khôi phục chat session, ghi tin nhắn và lịch sử. |
| `admin_routes.py` | API/trang quản trị tài khoản, vai trò, quyền và audit. |
| `admin_service.py` | Quy tắc nghiệp vụ quản trị, scope, transaction và cập nhật dữ liệu quyền. |
| `db.py` | Kết nối MySQL, cursor và ranh giới transaction dùng chung. |

### Chat, truy vấn và tạo câu trả lời

| File | Vai trò |
|---|---|
| `routing.py` | Chọn nhánh xử lý câu hỏi và nhóm nghiệp vụ phù hợp. |
| `question_language.py` | Chuẩn hóa tiếng Việt, nhận diện cách gọi tương đương và ngữ cảnh câu hỏi nối tiếp. |
| `query_planner.py` | Chuyển yêu cầu dữ liệu thành kế hoạch truy vấn có cấu trúc. |
| `query_plans.py` | Các mẫu/kế hoạch truy vấn được hỗ trợ, đặc biệt cho truy vấn an toàn, xác định trước. |
| `sql_service.py` | Điều phối câu hỏi SQL: tạo kế hoạch, thực thi truy vấn và trả bằng chứng. |
| `sql_safety.py` | Kiểm tra câu SQL và giới hạn thời gian/số dòng trước khi thực thi. |
| `sql_guard.py` | Các rào chắn bổ sung quanh SQL do model tạo hoặc dữ liệu trả về. |
| `llm_sql.py` | Tạo/điều phối SQL bằng mô hình ngôn ngữ theo schema context. |
| `schema_context.py` | Mô tả schema/ý nghĩa cột cho thành phần lập truy vấn. |
| `rag_service.py` | Tìm tài liệu liên quan và lọc kết quả theo quyền truy cập. |
| `ai_service.py` | Gọi model để tạo câu trả lời từ câu hỏi và bằng chứng đã truy xuất. |
| `answer_renderer.py` | Chuyển kết quả/bằng chứng có cấu trúc thành nội dung hiển thị. |
| `text_formatting.py` | Chuẩn hóa văn bản ở ranh giới hiển thị/lưu trả lời. |
| `chat_tools.py` | Chọn và chạy công cụ nghiệp vụ được phép gọi từ hội thoại. |
| `customer_chat.py` | Thu thập/nhận diện dữ liệu khách hàng được gửi dưới dạng hội thoại. |

### Tài liệu, khách hàng, dữ liệu và route nghiệp vụ

| File | Vai trò |
|---|---|
| `document_routes.py` | Endpoint upload, danh mục và truy cập tài liệu. |
| `document_service.py` | Lưu file, metadata, quyền và trạng thái trích xuất tài liệu. |
| `document_parser.py` | Đọc PDF/DOCX/XLSX và trích xuất văn bản/bảng. |
| `customer_input_routes.py` | API tạo/xem/sửa/xác nhận bản nháp nhập khách. |
| `customer_input.py` | Quy tắc chuẩn hóa, kiểm tra, staging và commit dữ liệu khách hàng. |
| `customer_file_import.py` | Chuyển nội dung tài liệu đã trích xuất thành batch nhập khách có thể review. |
| `excel_sync.py` | Đồng bộ dữ liệu đã commit với workbook theo quy trình dự án. |
| `chat_action_routes.py` | API công cụ chat, tải file khách và các thao tác chat như lịch hẹn. |
| `business_routes.py` | API đọc các danh sách nghiệp vụ như khách hàng/tồn kho. |
| `sales_routes.py` | API nghiệp vụ bán hàng/đơn hàng và chứng từ liên quan. |
| `operations_routes.py` | API danh mục sản phẩm và thao tác vận hành. |
| `stock_routes.py` | API nhập kho và các thao tác liên quan tồn kho. |
| `dashboard_routes.py` | Endpoint dashboard và widget. |
| `dashboard_service.py` | Dữ liệu widget, scope lọc và tổng hợp dashboard. |
| `database_service.py` | Các truy vấn dữ liệu tổng quát được dùng bởi giao diện/API hiện có. |
| `stock_service.py` | Quy tắc và thao tác nghiệp vụ tồn kho. |
| `appointment_service.py` | Đọc/cập nhật lịch hẹn với kiểm tra phạm vi/trạng thái. |
| `inventory_policy.py` | Quy tắc nghiệp vụ dùng chung cho số lượng/tình trạng tồn kho. |

### Khởi tạo và kiểm thử

| File | Vai trò |
|---|---|
| `init_db.py` | Khởi tạo/reset schema và áp dụng script SQL theo quy trình dự án. |
| `check_db.py` | Kiểm tra kết nối database và thông tin đếm phục vụ chẩn đoán. |
| `test_ai.py` | Kiểm thử pipeline AI, có thể cần cấu hình API model. |
| `test_sql.py` | Bộ câu hỏi kiểm tra định tuyến/truy vấn; có thể chạy trực tiếp để xem kết quả. |

## Cách đọc một luồng code

Khi lần theo chức năng, bắt đầu từ URL trong file `*_routes.py` hoặc endpoint
trong `app.py`; xem decorator quyền ngay trên route; tiếp tục theo lời gọi tới
service; cuối cùng kiểm tra truy vấn `db.cursor()` và cách response được dựng.
Nếu hành động đến từ chat, kiểm tra thêm điểm gọi trong `chat_tools.py` hoặc
`chat_action_routes.py`. Hãy tìm tên hàm bằng tìm kiếm workspace thay vì chỉ
dựa vào tên file.

Các comment nên giải thích **lý do, thứ tự xử lý, dữ liệu vào/ra và ranh giới
an toàn** khi điều đó không hiển nhiên. Không cần bình luận lại từng dòng cú
pháp; docstring của module/hàm và tài liệu luồng nghiệp vụ hữu ích hơn vì giữ
được mã nguồn gọn và dễ cập nhật.
