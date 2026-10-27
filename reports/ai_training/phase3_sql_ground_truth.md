# Phase 3 SQL Ground Truth

Phase 2/3 đã chạy 150 case trên database dev bằng `chatbot_ro`, chỉ SELECT và không lưu row values.

| Metric | Kết quả |
|---|---:|
| Case SQL | 105 |
| Query execute thành công | 105 |
| Validate/execute lỗi | 0 |
| Query cần LLM/template | 0 |
| SQL result correctness | NOT_RUN |

`expected_result` của pilot hiện mô tả assertion/shape nhưng chưa có snapshot fixture cố định cho mọi case. Vì vậy SELECT thành công không được đánh đồng với kết quả nghiệp vụ đúng. Ground truth chính xác cần fixture ẩn danh, branch/model/color cố định và phép so sánh giá trị trực tiếp.
