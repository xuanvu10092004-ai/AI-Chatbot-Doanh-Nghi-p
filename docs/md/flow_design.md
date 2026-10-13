# B5 - Thiết kế luồng hoạt động hệ thống AI Chatbot Doanh nghiệp
# Đây là tài liệu thiết kế trước khi code, giúp mình xác định câu hỏi của người dùng sẽ đi qua những bước nào trong hệ thống.
## 1. Mục tiêu

Bước này dùng để thiết kế luồng xử lý chính của hệ thống trợ lý AI doanh nghiệp.

Hệ thống cần xử lý được câu hỏi của người dùng và xác định câu hỏi đó nên lấy dữ liệu từ database hay từ tài liệu nội bộ.

---

## 2. Luồng hoạt động tổng quát

Người dùng nhập câu hỏi vào giao diện Chatbox.

Giao diện gửi câu hỏi đến Flask Backend.

Backend nhận câu hỏi và chuyển sang bộ phân loại câu hỏi.

Bộ phân loại xác định câu hỏi thuộc nhóm SQL hay RAG.

Nếu câu hỏi thuộc nhóm SQL, hệ thống truy vấn dữ liệu từ SQLite.

Nếu câu hỏi thuộc nhóm RAG, hệ thống tìm nội dung liên quan trong bảng documents.

Sau đó dữ liệu được gửi cho AI để tạo câu trả lời tự nhiên.

Cuối cùng câu trả lời được hiển thị lại trên giao diện Chatbox.

---

## 3. Sơ đồ luồng xử lý

User Question
→ Web Interface
→ Flask API
→ Question Routing
→ SQL hoặc RAG
→ Retrieve Data
→ Groq AI
→ AI Answer
→ Chatbox UI

---

## 4. Nhóm câu hỏi xử lý bằng SQL

Các câu hỏi SQL là những câu hỏi liên quan đến dữ liệu có cấu trúc trong database.

Ví dụ:

- Có bao nhiêu khách hàng?
- Khách hàng nào đang ở trạng thái tiềm năng?
- Khách hàng nào là VIP?
- Sản phẩm nào sắp hết hàng?
- Báo giá nào đã được duyệt?
- Cơ hội bán hàng nào có giá trị cao nhất?
- Tổng giá trị báo giá là bao nhiêu?

Các câu hỏi này sẽ lấy dữ liệu từ các bảng:

- customers
- inventory
- opportunities
- quotes
- chat_logs

---

## 5. Nhóm câu hỏi xử lý bằng RAG

Các câu hỏi RAG là những câu hỏi cần tìm thông tin trong tài liệu nội bộ.

Ví dụ:

- Chính sách chăm sóc khách hàng mới là gì?
- Quy định báo giá như thế nào?
- Khi nào sản phẩm được xem là tồn kho thấp?
- API key cần được bảo mật như thế nào?
- RAG trong hệ thống dùng để làm gì?
- Quy trình bàn giao hệ thống gồm những gì?

Các câu hỏi này sẽ lấy dữ liệu từ bảng:

- documents

---

## 6. Kết quả cần đạt

Sau bước B5, nhóm xác định được luồng xử lý chính của hệ thống.

Luồng này sẽ được dùng làm nền tảng để xây dựng các bước tiếp theo như:

- B6: Phân loại câu hỏi SQL hoặc RAG
- B7: Xây dựng giao diện web
- B8: Xây dựng backend Flask
- B9: Viết truy vấn SQL nền tảng
- B10: Tích hợp Groq API và RAG
## 7. Hình ảnh sơ đồ luồng

![Sơ đồ luồng xử lý AI Chatbot](docs/images/luong_xu_ly_ai_chatbot.png)