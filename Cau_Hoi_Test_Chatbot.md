# Danh sách câu hỏi kiểm thử (Test Cases) cho AI Chatbot

File này tổng hợp các câu hỏi đã được tối ưu để kiểm tra toàn bộ 6 module xử lý SQL và tính năng RAG (Tra cứu tài liệu nội bộ) của hệ thống. Bạn có thể copy/paste trực tiếp các câu hỏi này vào khung chat để xem AI phản hồi.

---

## 🛠️ I. KIỂM THỬ TRUY VẤN SQL (Cơ sở dữ liệu)

### Module 1: AI Chat & CRM (Khách hàng)
1. Có bao nhiêu khách hàng trong hệ thống?
2. Có bao nhiêu khách hàng VIP?
3. Liệt kê danh sách khách hàng mới.
4. **Top 10 khách hàng có doanh thu cao nhất là ai?** (Test logic JOIN 2 bảng)

### Module 2: AI CRM (Tương tác khách hàng)
5. **Khách hàng nào chưa phát sinh booking trong 90 ngày qua?** (Test tính năng lọc lịch sử giao dịch)

### Module 3: AI Opportunity (Cơ hội bán hàng)
6. Liệt kê tất cả cơ hội bán hàng.
7. Cơ hội bán hàng nào có giá trị cao nhất?
8. **Cơ hội bán hàng nào có khả năng chốt cao nhất?** (Test logic chuyển đổi sắp xếp sang cột Tỷ lệ thắng/Probability)
9. Các cơ hội nào đã thắng (won)?

### Module 4: AI Quote (Báo giá)
10. Có báo giá nào đang chờ duyệt không?
11. Danh sách báo giá đã được duyệt?
12. **Tạo quote cho CÔNG TY TNHH BÁN LẺ XYZ** (Test tính năng tự động tìm ID công ty và INSERT bản nháp vào CSDL) *(Lưu ý: Thay tên công ty bằng tên có thật trong Excel của bạn)*

### Module 5: AI Warehouse (Kho hàng)
13. Tổng số lượng sản phẩm trong kho là bao nhiêu?
14. Sản phẩm nào sắp hết hàng? (Tự động lấy mức < 10)
15. **Kho nào sắp hết hàng, mức tối thiểu 50?** (Test tính năng dùng Regex bắt tham số động từ câu hỏi)

### Module 6: AI Dashboard (Thống kê tổng quan)
16. Doanh thu hiện tại là bao nhiêu?
17. **Thống kê tổng quan hệ thống** (Hoặc gõ: *Tóm tắt tuần này*) - Sẽ hiển thị Khách hàng, Sản phẩm, Báo giá, Cơ hội, Booking và Doanh thu.

---

## 📚 II. KIỂM THỬ TÍNH NĂNG RAG (Tra cứu tài liệu nội bộ)

*(Lưu ý: Thuật toán Scoring RAG mới sẽ quét toàn bộ từ khóa để tìm đúng tài liệu)*

1. Quy định về thời gian phản hồi hỗ trợ khách hàng mới là bao lâu?
2. Chính sách chăm sóc khách hàng VIP của công ty là gì?
3. Hệ thống RAG và AI Chatbot hoạt động như thế nào?
4. Quy trình bàn giao hệ thống cho khách hàng bao gồm những bước nào?
5. Quy định bảo mật đối với API key và dữ liệu khách hàng được thực hiện ra sao?
6. Làm thế nào để phân loại khách hàng?
7. Quy trình xử lý báo giá bị từ chối là gì?
8. Quy định về việc đặt tên file trong dự án như thế nào?

---
*Mẹo: Bạn có thể gõ không dấu (vd: "top 10 khach hang doanh thu cao nhat") hệ thống vẫn sẽ hiểu và xử lý bình thường nhờ hàm `normalize_question`.*
