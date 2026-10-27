# System audit — AI Training Pilot

Ngày audit: 22/10/2026

## Phạm vi đã kiểm tra

| Thành phần | Bằng chứng trong repository | Trạng thái |
|---|---|---|
| LLM | `ai_service.py`, `llm_sql.py`; Groq được gọi khi có `GROQ_API_KEY` | Có tích hợp, chưa chạy API trong audit nếu thiếu key |
| SQL | `sql_service.py`, `sql_guard.py`, `sql_safety.py`, các view `v_ai_*` | Có whitelist/validator và query template |
| RAG | `rag_service.py`, `document_service.py`, `v_user_kb_access` | Có lọc quyền; cần fixture tài liệu để đo groundedness |
| Routing | `routing.py`, `access_control.py` | Có SQL/RAG/CLARIFY/DENY và nhận diện tự nhiên |
| Hội thoại | `chat_sessions`, `chat_messages`, follow-up trong `app.py` | Có lưu lịch sử và xử lý follow-up |
| Authentication | Flask session/backend identity, không lấy user từ giao diện | Có |
| Authorization | `authorize_intent`, permission/scope branch, audit log | Có kiểm tra trước truy xuất |
| Database | MySQL thật được dùng bởi test; dữ liệu đang thay đổi theo workspace | Không dùng làm ground truth cố định |

## Giới hạn môi trường

- Pilot không tự reset hoặc ghi/xóa dữ liệu MySQL production.
- Không có bước nào tuyên bố model đã fine-tune hay đã cập nhật trọng số.
- Test API Groq chỉ được chạy khi có `GROQ_API_KEY`; không có key thì trạng thái là `SKIP`, không phải `PASS`.
- SQL result correctness và RAG groundedness cần snapshot/fixture tái lập. Dataset chỉ mô tả assertion/nguồn cần kiểm tra, không bịa tồn kho, giá hoặc dữ liệu cá nhân.
- Dữ liệu cá nhân trong pilot là câu hỏi tổng quát; không đưa tên, email, số điện thoại thật vào dataset.

## Kiến trúc thực tế

Luồng chính là: phiên đăng nhập backend → phát hiện intent/quyền → route SQL hoặc RAG → query template/LLM SQL có validator → render bằng chứng. Groq dùng để sinh/diễn đạt trong các nhánh cần thiết; quyền, whitelist view và thao tác ghi vẫn do backend kiểm soát.

## Kết luận audit

Hệ thống đủ điều kiện chạy pilot định tuyến, intent, safety và regression. Chưa đủ bằng chứng để kết luận về độ đúng SQL nghiệp vụ, độ bám nguồn RAG, latency/token hoặc fine-tuning vì các phép đo đó cần API key và snapshot/fixture chuyên biệt. Những mục này được đánh dấu `BLOCKED/NOT_RUN` trong báo cáo baseline thay vì tạo kết quả giả.
