# Kết quả kiểm thử Honda AI Chatbot

Ngày ghi nhận: 2026-10-13

## Tổng hợp

| Nhóm | Kết quả | Ghi chú |
|---|---:|---|
| Validator SQL | Đạt | 8 passed, chạy không cần MySQL |
| Groq API | Skip | Thiếu `GROQ_API_KEY` |
| Kiểm thử MySQL/RBAC | Blocked | MySQL từ chối kết nối `127.0.0.1:3306` |

## Bộ câu hỏi chuẩn

Các đáp án được tính bằng SQL trực tiếp trong `tests/test_honda_mysql.py`, không hardcode kết quả. Chưa thể chạy do MySQL chưa khả dụng.

| # | Câu hỏi | SQL kỳ vọng | Kết quả |
|---:|---|---|---|
| 1 | SH 160i giá bao nhiêu? | `v_ai_products` theo `model_name` | Blocked |
| 2 | Giá niêm yết SH 160i | `MIN(list_price)` từ `v_ai_products` | Blocked |
| 3 | Có bao nhiêu phiên bản xe? | `COUNT(*)` từ `v_ai_products` | Blocked |
| 4 | Có bao nhiêu sản phẩm trong kho? | `COUNT(*)` từ `v_ai_inventory` | Blocked |
| 5 | Tồn kho tại chi nhánh NT01 | `COUNT(*)` lọc `branch_code` | Blocked |
| 6 | Có bao nhiêu khách hàng? | `COUNT(*)` từ `v_ai_customers` | Blocked |
| 7 | Có bao nhiêu khách hàng đã mua? | `COUNT(*)` lọc `customer_status` | Blocked |
| 8 | Có bao nhiêu đơn hàng? | `COUNT(DISTINCT order_id)` từ `v_ai_orders` | Blocked |
| 9 | Đơn hàng tại NT02 | `COUNT(DISTINCT order_id)` lọc `branch_code` | Blocked |
| 10 | Các mẫu xe tay ga | `COUNT(*)` lọc `segment = 'tay_ga'` | Blocked |

## Quyền cần chạy lại khi MySQL hoạt động

- Guest hỏi giá vốn: phải bị từ chối và có audit `denied`.
- Sales user 3 hỏi tồn kho: phải được phép.
- Kỹ thuật viên user 5 hỏi giá vốn: phải bị từ chối.
- Guest đọc tài liệu danh mục sales: phải bị từ chối.
