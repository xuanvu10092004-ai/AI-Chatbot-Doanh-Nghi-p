# Báo Cáo Triển Khai Chi Tiết: AI Chatbot Doanh Nghiệp

Dưới đây là tài liệu trình bày chi tiết từng bước mà nhóm đã thực hiện để xây dựng, tích hợp và triển khai hệ thống AI Chatbot hỗ trợ doanh nghiệp (CRM & Warehouse).

---

## Bước 1: Thiết kế Cơ sở Dữ liệu & Khởi tạo Schema (`init_db.py`)
- **Mục tiêu:** Xây dựng nền tảng lưu trữ dữ liệu (Database) cục bộ, nhẹ và dễ quản lý cho ứng dụng.
- **Công nghệ sử dụng:** SQLite3.
- **Chi tiết triển khai:**
  - Định nghĩa kiến trúc CSDL với 6 bảng cốt lõi phục vụ 3 nhóm nghiệp vụ chính:
    1. **CRM & Bán hàng:** `customers` (Khách hàng), `opportunities` (Cơ hội kinh doanh), `quotes` (Báo giá).
    2. **Kho hàng:** `inventory` (Sản phẩm & Tồn kho).
    3. **AI & Tri thức:** `documents` (Lưu tài liệu chính sách cho RAG), `chat_logs` (Lưu lịch sử hội thoại).
  - Bật tính năng kiểm tra khóa ngoại (`PRAGMA foreign_keys = ON`) để đảm bảo tính toàn vẹn dữ liệu giữa khách hàng, báo giá và sản phẩm.

## Bước 2: Chuẩn bị Dữ liệu & Xây dựng Pipeline ETL (`import_excel_to_db.py`)
- **Mục tiêu:** Tự động hóa quá trình nạp dữ liệu mẫu ban đầu từ file Excel vào Database.
- **Công nghệ sử dụng:** Pandas.
- **Chi tiết triển khai:**
  - Khởi tạo file dữ liệu mẫu `data_ai_chatbot_doanh_nghiep.xlsx` với các sheet tương ứng cấu trúc bảng.
  - Xây dựng luồng ETL (Extract - Transform - Load):
    - **Dọn dẹp CSDL cũ:** Script tự động xóa dữ liệu cũ theo thứ tự nghiêm ngặt (bảng con xóa trước, bảng cha xóa sau) để tránh lỗi Foreign Key, đồng thời reset chỉ số ID tự tăng.
    - **Làm sạch dữ liệu:** Xóa các dòng rỗng, ánh xạ tên cột tiếng Việt có chứa chú thích sang tên cột chuẩn trong CSDL, chuyển đổi các ô giá trị `NaN` thành `NULL`.
    - **Nạp dữ liệu:** Đẩy dữ liệu vào SQLite một cách tự động.

## Bước 3: Phát triển Module Nhận dạng Ý định (Routing & Classifier)
- **Mục tiêu:** Xác định luồng xử lý chính xác dựa trên câu hỏi của người dùng (Tra cứu CSDL hay Tra cứu Văn bản).
- **Chi tiết triển khai:**
  - File `routing.py` thực hiện xử lý ngôn ngữ tự nhiên cơ bản: chuyển chữ thường, loại bỏ dấu tiếng Việt để chuẩn hóa đầu vào.
  - Dựa vào bộ từ khóa (keywords matching) để phân loại:
    - Nhóm **SQL (Truy vấn Data):** Các từ khóa như "kho", "tồn", "doanh thu", "khách hàng", "báo giá"...
    - Nhóm **RAG (Tra cứu Tài liệu):** Các từ khóa như "chính sách", "quy định", "hướng dẫn"...

## Bước 4: Xây dựng Module Truy xuất Ngữ cảnh (Retrieval Services)
- **Mục tiêu:** Dựa vào ý định đã phân loại, trích xuất đúng thông tin làm ngữ cảnh (context) cho LLM.
- **Chi tiết triển khai:**
  - **Dịch vụ truy vấn CSDL (`sql_service.py`):** Viết các hàm thực thi mã SQL tổng hợp (như đếm số khách VIP, lọc hàng sắp hết).
  - **Dịch vụ truy vấn Tài liệu (`rag_service.py`):** Xây dựng công cụ tìm kiếm mô phỏng kỹ thuật RAG. Tách câu hỏi thành các từ khóa, loại bỏ "từ dừng" (stopwords), và dùng lệnh `LIKE` tìm kiếm nội dung/tiêu đề tài liệu trong bảng `documents`.

## Bước 5: Tích hợp Mô hình Ngôn ngữ Lớn LLM (`ai_service.py`)
- **Mục tiêu:** Sinh ra câu trả lời tự nhiên, thân thiện và chính xác dựa trên Context thu thập được.
- **Công nghệ sử dụng:** Groq API (Mô hình Llama-3).
- **Chi tiết triển khai:**
  - Cấu hình API Key và tên Model thông qua biến môi trường (file `.env`).
  - Xây dựng System Prompt với vai trò "Trợ lý AI Doanh nghiệp chuyên nghiệp".
  - Định nghĩa nguyên tắc nghiêm ngặt cho LLM: **Chỉ được trả lời dựa trên Context cung cấp, không tự bịa thông tin (No Hallucination)**.

## Bước 6: Phát triển Web Backend API (`app.py`)
- **Mục tiêu:** Giao tiếp giữa Giao diện người dùng và các Core Services của hệ thống.
- **Công nghệ sử dụng:** Flask.
- **Chi tiết triển khai:**
  - Tạo RESTful API cho Dashboard: `/api/dashboard`, `/api/low-stock`, `/api/potential-customers`.
  - Thiết lập API `/chat` (POST request): Nhận câu hỏi, gọi luồng Routing -> Retrieval -> Generator, và trả về JSON kết quả.
  - Tích hợp logic tự động mở trình duyệt web khi chạy app.

## Bước 7: Xây dựng Giao diện Người dùng (Frontend)
- **Mục tiêu:** Tạo ra một Dashboard trực quan và Cửa sổ Chat tương tác thời gian thực.
- **Công nghệ sử dụng:** HTML, CSS, JavaScript (Fetch API).
- **Chi tiết triển khai:**
  - Render giao diện tĩnh bằng thư mục `templates/` và `static/`.
  - Viết mã JS bất đồng bộ để gọi API điền dữ liệu vào các thẻ thống kê.
  - Lập trình giao diện Chat ( bong bóng chat, hiệu ứng typing, tự động cuộn trang) mang lại trải nghiệm người dùng hiện đại.

## Bước 8: Kiểm thử Độc lập (Unit Testing)
- **Mục tiêu:** Đảm bảo các logic hoạt động trơn tru trước khi ráp vào hệ thống Web.
- **Chi tiết triển khai:**
  - Viết script `test_sql.py` và `test_ai.py` để mô phỏng các câu hỏi và kiểm tra độ chính xác của SQL query cũng như tốc độ, chất lượng phản hồi từ Groq API.
