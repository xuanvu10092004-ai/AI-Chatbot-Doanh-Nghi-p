# Nơi lưu và quản lý tài khoản đăng nhập

Ứng dụng dùng database MySQL/MariaDB `honda_chatbot`, không dùng file SQLite `database.db`. Địa chỉ máy chủ và tên database lấy từ `.env`, thông qua `db.py`. Chạy `python check_db.py` để xem database đang kết nối và số bản ghi, không in thông tin bí mật.

## Các bảng liên quan

| Bảng/view | Ý nghĩa |
|---|---|
| `users` | Tài khoản: `id`, `email`, `full_name`, `password_hash`, `is_active`, chi nhánh và trạng thái khóa/đổi mật khẩu |
| `roles` | Vai trò và trang đến sau đăng nhập |
| `user_roles` | Gán vai trò, phạm vi chi nhánh và thời điểm hết hạn cho tài khoản |
| `permissions` | Các mã quyền, ví dụ `user:manage` |
| `role_permissions` | Quyền của vai trò và phạm vi `all`/`branch`/`own` |
| `v_user_permissions` | Quyền hiệu lực dùng để kiểm tra từng yêu cầu backend |
| `rbac_audit_log` | Nhật ký đăng nhập và thay đổi tài khoản/quyền |

Kiểm tra ngày 14/10/2026: 89 tài khoản, gồm 9 tài khoản demo và 80 khách hàng mô phỏng. Khách id 101-180 có hash giả, không đăng nhập được. Mật khẩu demo lấy từ `DEMO_ACCOUNT_PASSWORD`, được hash bằng Werkzeug; không lưu mật khẩu thuần trong bảng hoặc tài liệu.

## Quản lý trên giao diện

Đăng nhập tài khoản có quyền `user:manage`, mở `/admin/users` để tạo tài khoản, khóa/mở khóa, đặt lại mật khẩu và gán/gỡ vai trò. Quản lý vai trò tại `/admin/roles`, quyền tại `/admin/permissions` cần quyền `rbac:manage` toàn hệ thống. Nhật ký nằm tại `/admin/audit`, cần `audit:read`.

Các trang và API quản trị đều kiểm tra quyền ở server, không chỉ ẩn nút. Các yêu cầu ghi cần CSRF. Phạm vi chi nhánh và giới hạn gán quyền được kiểm tra trong `admin_service.py`.

## Luồng đăng nhập trong source

1. `auth_routes.py`: `/login` nhận email và mật khẩu, gọi `security.authenticate`.
2. `security.py`: truy vấn `users` bằng tham số SQL, kiểm tra hash, trạng thái hoạt động và khóa; ghi audit. Sai 5 lần khóa 15 phút.
3. Đăng nhập thành công xóa phiên cũ, lưu `session['user_id']`. Mỗi request, `initialize_request` tải lại tài khoản và vai trò từ database.
4. `app.py`: chatbot lấy danh tính từ `g.user` đã xác thực. Không lấy user id từ JSON hoặc header giả danh.
5. `admin_routes.py` và `admin_service.py`: quản lý tài khoản/quyền với kiểm tra scope, transaction và audit.

`DB_USER`/`DB_PASSWORD` là tài khoản **kết nối database**, khác với tài khoản **đăng nhập website** trong `users`. `chatbot_ro` là tài khoản MySQL chuyên đọc các view AI; không dùng để đăng nhập giao diện.

## Logo và câu trả lời

Theo yêu cầu trực tiếp của người dùng, ảnh `docs/images/logo.jpg` được sao chép nguyên vẹn vào `static/images/logo.jpg`, dùng trong thanh đầu trang và trang đăng nhập. Ảnh JPG có nền caro được ghép sẵn trong ảnh, không phải nền trong suốt. Giao diện vẫn ghi rõ dữ liệu mô phỏng.

`static/chat-formatting.js` chuyển dấu đậm/nghiêng thành `strong`/`em`, hỗ trợ danh sách và tiêu đề, không dùng `innerHTML`. Đây là bộ định dạng giới hạn, không phải bộ Markdown đầy đủ; HTML đầu vào luôn là văn bản, liên kết không được thực thi. `static/chat.js` gọi bộ định dạng trước khi bổ sung bảng số liệu và nguồn.

`text_formatting.py` đổi dấu gạch dài sang `-` trước khi lưu câu trả lời và trả API. Giao diện áp dụng cùng quy tắc cho tiêu đề nguồn và nội dung ô bảng. `ai_service.py` có chỉ dẫn định dạng cho các lượt sinh câu trả lời sau này. Các phần code mới có comment/docstring giải thích mục đích, luồng dữ liệu và ranh giới an toàn.
