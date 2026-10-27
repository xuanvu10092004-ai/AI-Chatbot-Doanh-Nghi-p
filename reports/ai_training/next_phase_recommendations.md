# Next Phase Recommendations

1. Nhận phê duyệt rõ ràng để tạo database fixture cô lập không chứa dữ liệu khách hàng thật, hoặc cung cấp fixture đã ẩn danh.
2. Chạy `/chat` bằng test client trên fixture và rollback/dọn dữ liệu trong chính database đó.
3. Thêm fixture tài liệu public/sales để đo RAG groundedness và nguồn trích dẫn.
4. Cấu hình `GROQ_API_KEY` qua secret manager, chạy 10 câu smoke trước rồi mới chạy 150 câu.
5. Chỉ tối ưu prompt bằng Development; giữ Validation/Test độc lập.
6. Chưa có bằng chứng cần fine-tuning; ưu tiên routing, SQL/RAG và authorization.
