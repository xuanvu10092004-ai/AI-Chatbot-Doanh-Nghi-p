# Real AI Evaluation Baseline

Ngày chạy: 22/10/2026  
Phạm vi: **toàn bộ 150 câu**

## Trạng thái thực thi

| Hạng mục | Kết quả |
|---|---:|
| Groq request | 0 |
| SELECT thực tế qua `chatbot_ro` | 105 |
| SQL bị block vì cần LLM/template | 0 |
| SQL lỗi khi validate/thực thi | 0 |
| RAG E2E | BLOCKED |
| Flask E2E có session/audit | BLOCKED |
| Case safety/clarification preflight | 45 |

Database đã dùng: `honda_chatbot` (database dev hiện tại). Không ghi, sửa hoặc xóa dữ liệu; report không chứa row values hay PII.

## Latency SELECT

- Số query đo được: **105**
- Trung bình: **6.60 ms**
- P95: **19.62 ms**

Đây là kết quả thực thi query/plan, chưa phải accuracy của câu trả lời cuối vì chưa gọi Groq và chưa chạy full `/chat` trên fixture cô lập.
