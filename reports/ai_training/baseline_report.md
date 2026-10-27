# AI Training Pilot — Baseline Report

> Đây là baseline offline của pilot 150 câu. Chưa gọi Groq, chưa thực thi SQL và chưa đọc dữ liệu production.

- Tổng số case: **150**
- Development/Validation/Test: **100/25/25**
- SQL intent + route + plan shape: **105/105**
- Non-SQL route (RAG/CLARIFY/DENY): **45/45**

| Nhóm lỗi | Số lượng |
|---|---:|
| pass | 150 |
| intent | 0 |
| route | 0 |
| sql_plan | 0 |

## Metrics chưa thể chạy an toàn

| Metric | Trạng thái | Lý do |
|---|---|---|
| SQL result correctness | NOT_RUN | Cần MySQL snapshot/fixture cố định; không dùng dữ liệu đang thay đổi làm đáp án cứng |
| RAG groundedness | NOT_RUN | Cần bộ tài liệu fixture và nguồn kỳ vọng |
| Answer correctness | NOT_RUN | Cần chạy full `/chat` với identity test và bằng chứng |
| Latency/token usage | NOT_RUN | Chưa gọi Groq/API |
| Permission compliance | PRECHECK ONLY | Case safety đã route deny; cần integration test bằng session/backend identity |

## Các case lỗi

| ID | Expected route | Actual route | Nhóm |
|---|---|---|---|
| Không có | - | - | - |

## Kết luận

Pilot đạt tiêu chí preflight định tuyến hiện tại. Đây chưa phải kết quả training và chưa đủ để kết luận chatbot trả lời đúng dữ liệu nghiệp vụ. Bước kế tiếp là chạy trên fixture/snapshot read-only, sau đó mới tối ưu bằng tập Development; không dùng Validation/Test để few-shot.
