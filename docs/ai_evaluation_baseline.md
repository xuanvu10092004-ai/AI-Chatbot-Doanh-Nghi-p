# AI Evaluation Baseline

> Báo cáo được tạo bởi `python scripts/ai_evaluation.py benchmark`. Đây là baseline của route/quy tắc hiện tại, không phải kết quả fine-tuning.

- Tổng số câu: **200**
- Intent đúng: **200/200**
- Route đúng: **200/200**
- SQL plan hợp lệ hoặc được đánh dấu cần LLM: **200/200**

| Nhóm lỗi | Số lượng | Tỷ lệ |
|---|---:|---:|
| pass | 200 | 100.0% |
| intent | 0 | 0.0% |
| route | 0 | 0.0% |
| sql_plan | 0 | 0.0% |

## Phân bố theo split

| Split | Số câu |
|---|---:|
| development | 160 |
| evaluation | 40 |

## Câu cần xử lý

| ID | Nhóm lỗi | Intent thực tế | Route thực tế |
|---|---|---|---|
| Không có | - | - | - |

## Cách diễn giải

- `intent`: mở rộng bộ nhận diện hoặc sửa câu hỏi/nhãn.
- `route`: kiểm tra phân loại SQL/RAG/clarify trước khi gọi model.
- `sql_plan`: bổ sung query template hoặc đưa vào tập kiểm thử LLM.
- Kết quả này không được dùng để khẳng định dữ liệu nghiệp vụ; kết quả SQL phải được kiểm tra trên snapshot/fixture tái lập.
