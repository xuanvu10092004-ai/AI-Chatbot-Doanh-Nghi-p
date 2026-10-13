# AI Chatbot Doanh Nghiep

Ung dung Flask ke thua he thong AI CRM/RAG hien co va nang cap cho du lieu Honda. Muc tieu dot thuc tap la bo sung phan quyen da cap, trich xuat du lieu co kiem soat, doc tai lieu da dinh dang va tich hop an toan voi 6 module AI hien huu.

## Pham vi hien tai

- Du lieu MySQL 8.0.16+ voi san pham, phien ban, ton kho, khach hang va don hang Honda.
- Text-to-SQL chi truy van cac view `v_ai_*`, khong truy cap bang goc.
- Validator chi cho phep mot cau `SELECT`, whitelist view, gioi han `LIMIT` va thoi gian chay.
- RBAC, quyen theo chi nhanh, kiem tra quyen truoc truy xuat va audit.
- RAG gioi han theo quyen, tra nguon va noi ro khi khong co bang chung.
- 6 module: CRM, Warehouse, Opportunity, Quote, Dashboard va AI Chat/RAG.

## Cau truc quan trong

- `app.py`: entry point Flask va API.
- `db.py`: pool MySQL cho ung dung va tai khoan doc rieng cho text-to-SQL.
- `routing.py`: phan loai module va huong SQL/RAG.
- `schema_context.py`: tao schema context tu metadata/comment cua `v_ai_*`.
- `sql_safety.py`: kiem tra SQL do LLM sinh.
- `sql_service.py`, `rag_service.py`: truy xuat du lieu/tai lieu co kiem soat.
- `data/schema/extensions/`: view AI, tai khoan doc va index mo rong.
- `tests/`: test validator va MySQL/RBAC.
- `docs/md/`: bao cao, ke hoach, thiet ke luong va bo cau hoi.

## Cai dat

Yeu cau Python 3.13+, MySQL 8.0.16+ va tai khoan MySQL co quyen khoi tao schema/view/index/user.

```powershell
python -m pip install -r requirements.txt
```

Tao `.env` tu `.env.example` va dien:

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=...
DB_PASSWORD=...
DB_NAME=honda_chatbot
CHATBOT_RO_PASSWORD=...
GROQ_API_KEY=...
APP_ENV=dev
```

Khong commit `.env` hoac mat khau vao SQL. Tai khoan text-to-SQL dung `CHATBOT_RO_PASSWORD` va chi co `SELECT` tren cac view `v_ai_*`.

## Khoi tao va chay

```powershell
python init_db.py --reset
python app.py
```

Script ap dung schema chuan, du lieu mau va cac extension theo thu tu `02_ai_views.sql`, `03_chatbot_ro_user.sql`, `04_indexes.sql`.

## Kiem thu

```powershell
python -m pytest -q
```

Test validator khong can MySQL. Test MySQL/RBAC se skip hoac ghi nhan blocked khi MySQL chua chay; test Groq tu skip neu thieu `GROQ_API_KEY`. Ket qua gan nhat o [docs/test_results.md](docs/test_results.md).

## Ke hoach thuc tap 12 tuan

Thoi gian: **12/10/2026 - 03/01/2027**.

1. Tuan 01: khao sat he thong cu, chot pham vi va test hoi quy.
2. Tuan 02: thiet ke kien truc, du lieu, RBAC va quy trinh tai lieu.
3. Tuan 03-04: dang nhap, phien/token, nguoi dung, vai tro va quyen.
4. Tuan 05-06: PDF/DOCX/XLSX, OCR anh/PDF scan, preview va xac nhan truoc ghi DB.
5. Tuan 07: kho tri thuc, chunking/embedding, truy xuat va nguon.
6. Tuan 08-09: tich hop 6 module, phan quyen truoc truy xuat va ghi co xac nhan.
7. Tuan 10: kiem thu tich hop, hoi quy, bao mat va du lieu sai.
8. Tuan 11-12: dong goi demo, bao cao, slide, sua loi va nghiem thu.

Chi tiet phan cong va tieu chi nghiem thu o [docs/md/Bao_cao_Trien_khai_Chi_tiet.md](docs/md/Bao_cao_Trien_khai_Chi_tiet.md).# AI Chatbot Doanh Nghiệp (Enterprise AI Chatbot)

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

## MySQL Honda Chatbot

Yêu cầu MySQL 8.0.16+ và Python 3.13+. Cài dependency:

```powershell
python -m pip install -r requirements.txt
```

Tạo `.env` từ `.env.example` và điền `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME=honda_chatbot`, `CHATBOT_RO_PASSWORD` và tùy chọn
`GROQ_API_KEY`. Không commit `.env`.

Khởi tạo lại schema, seed và các extension theo thứ tự:

```powershell
python init_db.py --reset
```

Chạy test:

```powershell
python -m pytest -q
```

Các test cần MySQL thật sẽ tự skip nếu server chưa chạy; test Groq tự skip khi
thiếu `GROQ_API_KEY`. Các module Opportunity, Quote và Booking trả HTTP 501 cho
đến khi có schema-extension chính thức.
