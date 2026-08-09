# AI Chatbot Doanh Nghiệp (Enterprise AI Chatbot)

Đây là một ứng dụng Web (Flask) tích hợp Trí tuệ nhân tạo (AI Chatbot) được thiết kế cho các doanh nghiệp để quản lý Quan hệ khách hàng (CRM) và Quản lý Kho hàng (Warehouse). Hệ thống sử dụng mô hình ngôn ngữ lớn (Groq LLM) để phản hồi người dùng thông qua xử lý ngôn ngữ tự nhiên (NLP) kết hợp truy vấn cơ sở dữ liệu (SQL) và truy xuất tài liệu (RAG).

## Tính năng nổi bật

- **Dashboard Thống Kê**: Hiển thị tổng quan số liệu từ cơ sở dữ liệu (số lượng khách hàng, kho hàng, cơ hội, báo giá, tài liệu và lịch sử chat).
- **Cảnh Báo Tồn Kho**: Tự động lấy và hiển thị danh sách các sản phẩm sắp hết hàng (số lượng < 10) từ CSDL.
- **Khách Hàng Tiềm Năng**: Phân loại và hiển thị nhóm khách hàng trọng tâm (VIP, Potential, New).
- **Chatbot AI Thông Minh**:
  - Tự động phân loại câu hỏi (Routing) thành dạng truy vấn Cơ sở dữ liệu (SQL) hoặc hỏi đáp dựa trên tài liệu (RAG).
  - Truy xuất tự động dữ liệu liên quan làm ngữ cảnh (Context) cho LLM.
  - Sử dụng LLM qua Groq API để sinh câu trả lời tự nhiên, chính xác, bám sát dữ liệu của doanh nghiệp.
- **Quản trị dữ liệu dễ dàng**: Cung cấp công cụ tự động tạo Database SQLite và import dữ liệu mẫu hàng loạt từ file Excel.

## Cấu trúc Dự án

- `app.py`: Tệp tin chạy chính (Entry Point) của ứng dụng Flask Web Server. Định nghĩa các API endpoint (`/`, `/chat`, `/api/dashboard`, `/api/low-stock`, `/api/potential-customers`).
- `database_service.py`: Tầng truy xuất dữ liệu (Data Access Layer - DAL), chứa các hàm xử lý SQL để lấy các báo cáo thống kê phục vụ Frontend.
- `init_db.py`: Script khởi tạo cấu trúc schema CSDL SQLite (`database.db`) với các bảng: `customers`, `inventory`, `opportunities`, `quotes`, `documents`, `chat_logs`.
- `import_excel_to_db.py`: Script ETL hỗ trợ nạp dữ liệu từ file Excel (`data_ai_chatbot_doanh_nghiep.xlsx`) vào SQLite.
- `routing.py`: Thuật toán xử lý phân loại ý định câu hỏi của người dùng (Xác định dùng SQL hay RAG và thuộc Module nào).
- `sql_service.py`: Xử lý truy xuất thông tin từ CSDL để làm ngữ cảnh trả lời (dành cho các câu hỏi lấy số liệu có cấu trúc).
- `rag_service.py`: Xử lý tìm kiếm tài liệu từ nội bộ công ty (Retrieval-Augmented Generation).
- `ai_service.py`: Giao tiếp với API của Groq LLM để tạo câu trả lời dựa trên câu hỏi và context thu thập được.

## Hướng dẫn Cài đặt & Chạy ứng dụng

### 1. Cài đặt các thư viện cần thiết
Bạn cần có Python trên máy. Mở terminal/command prompt và chạy:
```bash
pip install flask pandas openpyxl
```
*(Nếu hệ thống của bạn yêu cầu thêm các thư viện khác như `groq`, hãy cài đặt thêm bằng lệnh `pip install groq`)*

### 2. Khởi tạo Cơ sở dữ liệu
Chạy script để tạo file `database.db` và cấu trúc các bảng. Bỏ qua bước này nếu bạn đã có file CSDL:
```bash
python init_db.py
```

### 3. Nạp dữ liệu mẫu
Để nhập dữ liệu vào CSDL từ file Excel `data_ai_chatbot_doanh_nghiep.xlsx`, hãy chạy lệnh sau:
```bash
python import_excel_to_db.py
```
*Lưu ý: Hành động này sẽ làm sạch các bảng và nạp lại dữ liệu mới từ file Excel.*

### 4. Khởi chạy Ứng dụng Web
Chạy file `app.py` để bật server Flask:
```bash
python app.py
```
Hệ thống sẽ chạy Web Server cục bộ và tự động mở trình duyệt web của bạn.
