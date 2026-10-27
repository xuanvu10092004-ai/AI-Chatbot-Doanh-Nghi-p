# Phase 3 Final Report

## Before/After

| Metric | Phase 2 baseline | Phase 3 after | Sample size |
|---|---:|---:|---:|
| Deterministic SQL execution | 89 | 105 | 105 SQL cases |
| SQL execution errors | 0 | 0 | 105 |
| SQL blocked | 16 | 0 | 105 |
| Groq/LLM accuracy | NOT_RUN | BLOCKED | 0 |
| RAG groundedness | NOT_RUN | BLOCKED | 0 |
| Flask E2E | NOT_RUN | BLOCKED | 0 |
| Generalization route | 26/30 before fix | 30/30 regression retest | 30 |
| SELECT latency P95 | 6.39 ms | 19.62 ms | 105 |

## Đã thực hiện

- Chạy 105 SELECT thật bằng `chatbot_ro` trên database dev, không ghi row values/PII.
- Bổ sung template deterministic cho các nhóm truy vấn bị block; block giảm từ 16 xuống 0.
- Sửa routing theo nguyên nhân gốc: câu hỏi ngắn thiếu đối tượng -> CLARIFY; `ask_price_list` -> SQL; phủ định/vượt quyền tự nhiên -> DENY.
- Chạy 150 case và ghi record redacted tại `phase3_case_records.jsonl`.
- Tạo fixture SQL tổng hợp tại `data/ai_training/fixtures/honda_chatbot_test.sql`; chưa import tự động để tránh đụng database đang có dữ liệu.
- Không tạo API key giả, không fine-tune và không gọi Groq khi thiếu key.

## Chưa thể kết luận

`GROQ_API_KEY` chưa có nên chưa thể đo LLM accuracy, token usage, câu trả lời cuối hoặc gọi API thật. Full Flask/RAG E2E trên database cô lập cũng chưa chạy vì fixture mới chỉ được tạo thành file SQL, chưa được chủ động import. Các hướng dẫn import nằm trong `data/ai_training/fixtures/README.md`.

Trạng thái chính xác: **PARTIAL / BLOCKED**, không phải PASS toàn bộ Phase 3.

## Cách mở khóa

1. Cấu hình `GROQ_API_KEY` thật trong PowerShell theo README.
2. Import fixture vào đúng database `honda_chatbot_test` theo README fixture và cấp quyền read-only cần thiết bằng mật khẩu do người vận hành cung cấp.
3. Chạy smoke 10 case trước, sau đó mới chạy bộ 150 case.