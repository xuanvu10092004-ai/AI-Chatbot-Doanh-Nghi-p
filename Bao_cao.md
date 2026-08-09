# Báo Cáo Dự Án: AI Chatbot Doanh Nghiệp (Enterprise AI Chatbot)

## 1. Tổng quan Dự án

Dự án **AI Chatbot Doanh Nghiệp** là một hệ thống web thông minh được xây dựng bằng framework **Flask (Python)**. Hệ thống được thiết kế để hỗ trợ doanh nghiệp tối ưu hóa quá trình Quản lý Quan hệ Khách hàng (CRM) và Quản lý Hàng tồn kho (Warehouse). 

Điểm nổi bật của dự án là việc ứng dụng hệ thống **Trí tuệ nhân tạo (AI)** sử dụng mô hình ngôn ngữ lớn (LLM) thông qua Groq. AI Chatbot trong hệ thống không chỉ là một bot trò chuyện thông thường mà có khả năng tự động nhận diện ý định của người dùng, phân loại xem cần phải truy xuất dữ liệu từ các bảng SQL hay tra cứu tài liệu từ kho tri thức nội bộ (RAG - Retrieval-Augmented Generation). Nhờ đó, câu trả lời do AI sinh ra luôn chính xác, bám sát với thực trạng doanh nghiệp và loại bỏ tối đa tình trạng "ảo giác" (hallucination) thường gặp ở các LLM truyền thống.

## 2. Kiến trúc Hệ thống

### 2.1 Backend (Flask Web Service)
- **Framework:** Python Flask được sử dụng làm Web Server.
- **RESTful APIs:** Cung cấp các endpoint để giao tiếp với Frontend:
  - `/api/dashboard`: Cung cấp số liệu đếm tổng quan các thực thể trong CSDL.
  - `/api/low-stock`: Cảnh báo các mặt hàng có tồn kho dưới 10.
  - `/api/potential-customers`: Danh sách các khách hàng thuộc nhóm cần chăm sóc (VIP, Potential, New).
  - `/chat`: Endpoint xử lý chính, nhận câu hỏi từ người dùng và phản hồi đáp án AI.
- **AI Processing Pipeline:**
  - **Routing (`routing.py`):** Phân loại câu hỏi để định hướng cách xử lý (`SQL` hoặc `RAG`).
  - **Context Retrieval (`sql_service.py` & `rag_service.py`):** Dựa trên kết quả phân loại để query vào Database lấy ngữ cảnh (Context).
  - **Generation (`ai_service.py`):** Đóng gói câu hỏi và ngữ cảnh, gửi lên Groq LLM để tổng hợp thành câu trả lời văn bản tự nhiên.
  
### 2.2 Database (SQLite)
- Hệ thống sử dụng CSDL quan hệ **SQLite** (`database.db`) giúp thao tác nhanh và gọn nhẹ.
- **Sơ đồ các bảng chính (Schema):**
  - `customers`: Chứa thông tin đối tác/khách hàng.
  - `inventory`: Quản lý danh mục hàng hóa, số lượng, đơn giá.
  - `opportunities`: Lưu trữ các cơ hội bán hàng với khách hàng.
  - `quotes`: Quản lý báo giá phát hành.
  - `documents`: Đóng vai trò là Vector/Knowledge Database chứa các văn bản chính sách phục vụ pipeline RAG.
  - `chat_logs`: Lưu vết lịch sử trò chuyện để thống kê hoặc cải tiến bot.

### 2.3 Quá trình Xử lý Dữ liệu (ETL)
- Cấu trúc CSDL được tự động hóa khởi tạo qua `init_db.py`.
- Dữ liệu được dễ dàng quản trị thông qua Excel (`data_ai_chatbot_doanh_nghiep.xlsx`) và sử dụng Pandas trong file `import_excel_to_db.py` để tự động làm sạch (clean data), đổi tên cột (rename), và nạp (load) vào các bảng SQLite một cách chính xác.

### 2.4 Frontend
- Giao diện người dùng Single Page Application (SPA) thân thiện, tích hợp các widget cập nhật thời gian thực bằng Javascript Fetch API.
- Cửa sổ trò chuyện (Chat window) cho phép tương tác trực tiếp, sinh động với backend AI.

## 3. Các Luồng Nghiệp vụ Chính (Workflows)

### 3.1 Luồng Khởi tạo và Quản trị dữ liệu
1. Chạy `init_db.py` để tạo cấu trúc schema (chạy một lần).
2. Xây dựng và cập nhật bộ dữ liệu thực tế tại file Excel.
3. Chạy `import_excel_to_db.py` để đồng bộ dữ liệu vào hệ thống. Các bảng con được ưu tiên xóa trước để bảo toàn tính toàn vẹn của Khóa Ngoại (Foreign Key), sau đó tự động nạp dữ liệu mới vào.

### 3.2 Luồng Xử lý Chatbot AI (AI Core Flow)
1. **Tiếp nhận:** Người dùng đặt câu hỏi trên UI. Web gửi POST request định dạng JSON tới `/chat`.
2. **Phân loại (Router):** Backend nhận dữ liệu, gọi `route_question()`. Phân loại được xác định.
3. **Thu thập Ngữ cảnh (Retriever):**
   - Nếu dạng **SQL**: Trích xuất dữ liệu thực tế từ hệ thống kho hoặc CRM (`sql_service.py`).
   - Nếu dạng **RAG**: Tìm các chính sách/hướng dẫn liên quan trong bảng `documents` (`rag_service.py`).
4. **Sinh đáp án (Generator):** Gọi API qua `ai_service.py`, LLM phân tích Câu hỏi và Context được cấp để sinh câu trả lời ngôn ngữ tự nhiên.
5. **Phản hồi:** Đóng gói JSON trả về cho Frontend render lên khung chat.

## 4. Kết luận và Hướng Phát triển
- **Đạt được:** Xây dựng thành công ứng dụng Web hoàn chỉnh đóng vai trò như một hệ thống ERP/CRM tinh gọn được tăng cường sức mạnh bởi AI. 
- **Giải quyết vấn đề:** Giúp tự động hóa trả lời khách hàng, tiết kiệm thời gian tra cứu dữ liệu thủ công, kết hợp được tư duy suy luận của LLM và tính chính xác của dữ liệu CSDL nội bộ.
- **Hướng phát triển tương lai:** 
  - Nâng cấp phần RAG bằng cách áp dụng Vector Database (như ChromaDB hay Pinecone) và Embedding thay vì dùng bảng documents SQLite để tăng độ chính xác tìm kiếm ngữ nghĩa.
  - Tích hợp thêm xác thực người dùng (Authentication/Login).
  - Hỗ trợ biểu đồ trực quan (Charts) trên Dashboard dựa trên dữ liệu thu thập được.
