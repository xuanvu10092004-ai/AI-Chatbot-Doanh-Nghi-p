# Phase 3 Environment & Integration Audit

Ngày kiểm tra: 22/10/2026

| Thành phần | Kết quả thực tế |
|---|---|
| Groq client | Có trong `ai_service.py`; model lấy từ `GROQ_MODEL`, mặc định trong code là `llama-3.3-70b-versatile` |
| Model `.env` | `openai/gpt-oss-20b` |
| `GROQ_API_KEY` | Thiếu; không gọi request và không tạo key giả |
| MySQL | Kết nối được `127.0.0.1:3306`, database `honda_chatbot` |
| `chatbot_ro` | Đọc được `v_ai_products`; Phase 2 đã chạy SELECT thật bằng tài khoản này |
| Flask endpoint | `/chat` tồn tại; ghi `chat_sessions`/`chat_messages` nên chưa chạy trực tiếp trên DB không cô lập |
| RAG | `rag_service.py` và `v_user_kb_access` tồn tại; cần fixture tài liệu + session để đo groundedness |
| Context | Có `chat_sessions`, `chat_messages` và xử lý follow-up trong `app.py` |

## Kết luận

Tích hợp code tồn tại, nhưng Real Groq và full Flask/RAG E2E đang **BLOCKED** bởi thiếu API key và database fixture cô lập. Không sao chép PII, không ghi credentials vào log/report.
