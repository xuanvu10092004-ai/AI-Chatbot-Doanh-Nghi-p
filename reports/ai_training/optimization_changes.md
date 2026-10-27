# Optimization Changes

Phase 2 đã xác minh query read-only thực tế. Dựa trên 16 case ban đầu bị block, đã bổ sung template deterministic cho liệt kê sản phẩm/khách hàng và bộ lọc giá dưới ngưỡng; lần chạy lại giảm BLOCKED từ 16 xuống 0. Chưa thay đổi prompt/trọng số Groq hoặc RAG.

Các thay đổi đã có bằng chứng từ pilot trước Phase 2:

- Mở rộng nhận diện câu tự nhiên cho tồn kho, khách hàng, đơn hàng và giá vốn.
- Route sớm `RAG`, `CLARIFY`, `DENY`, `OUT_OF_SCOPE` cho câu hỏi tương ứng.
- Giữ validator SQL AST và tài khoản `chatbot_ro`; không hardcode câu trả lời nghiệp vụ.

Chưa có thay đổi model/trọng số.
