# Kết quả kiểm thử chatbot Honda

Ngày kiểm chứng: 13/10/2026. Môi trường: Python 3.13, MariaDB 10.4.32 (XAMPP), localhost:3306.

| Kiểm tra | Kết quả thực tế |
|---|---|
| `python init_db.py --create-if-missing` | Thành công; tạo database mới không chạy DROP DATABASE |
| Chạy lại `--create-if-missing` và `--extensions-only` | Thành công; số dòng không đổi |
| `python -m pytest -q` | **69 passed, 2 skipped in 0.53s** |
| Hai test gọi Groq thật | Skip vì thiếu `GROQ_API_KEY` |
| HTTP `GET /` | 200 |
| HTTP `/api/dashboard`, `/api/low-stock`, `/api/potential-customers` | 200 |
| HTTP `/chat`: SH 160i | 200, ba phiên bản; engine=database |
| HTTP `/chat`: guest hỏi giá vốn | 200, từ chối chung chung, audit denied |
| Phiên và lịch sử | Hai câu dùng cùng session; lưu user/bot và một audit mỗi lượt |
| Sales NT01 hỏi NT02 | Không có kết quả; không lộ dữ liệu NT02 |
| Tài khoản `chatbot_ro` đọc bảng gốc hoặc DELETE view | Lỗi 1142, đã kiểm chứng |
| Guest đọc RAG | Chỉ public, branch_id NULL; có nguồn id + tiêu đề |
| SQL validator | AST kiểm tra CTE, UNION, subquery, whitelist, giới hạn dòng, chặn biến phiên/hàm nguy hiểm |
| Timeout MariaDB và reset biến scope | Có timeout 5 giây, scope không rò qua pool |
| Payload prompt | System prompt và evidence riêng; kiểm chứng bằng client giả, chưa gọi model thật |

Dữ liệu nghiệp vụ: products=10, product_variants=28, inventory=84, users id>100=80, customer_profiles=80, orders=30.

## Mười câu chuẩn

Kết quả backend được đối chiếu với SQL trực tiếp trên bảng gốc trong `tests/test_chat_flow.py`; các giá trị dưới đây được lấy từ truy vấn thật khi viết báo cáo.

| # | Câu hỏi | Kết quả SQL trực tiếp | Đối chiếu backend |
|---|---|---|---|
| 1 | SH 160i giá bao nhiêu? | 92500000; 96500000; 100500000 | PASS |
| 2 | Có bao nhiêu khách hàng đã mua xe? | 30 | PASS |
| 3 | Tổng số đơn hàng? | 30 | PASS |
| 4 | Tổng tồn kho toàn hệ thống? | 451 | PASS |
| 5 | Mỗi phân khúc có bao nhiêu phiên bản? | xe_so, 7; tay_ga, 18; con_tay, 3 | PASS |
| 6 | Mẫu xe nào có giá niêm yết cao nhất? | SH 160i, SH 160i - Thể thao - Đỏ đen, 100500000 | PASS |
| 7 | Tổng doanh thu thuần của các đơn? | 1359600000 | PASS |
| 8 | Bao nhiêu khách hàng chọn trả góp? | 42 | PASS |
| 9 | Có bao nhiêu dòng tồn kho đang hết hàng? | 9 | PASS |
| 10 | Vision 110 có bao nhiêu phiên bản? | 3 | PASS |

## Giới hạn còn lại

- Không chạy `python init_db.py --reset`: prompt yêu cầu giữ dữ liệu, nên dùng chế độ tạo mới không DROP và áp dụng extension giữ dữ liệu. Chưa đạt tiêu chí kiểm chứng hai lần reset.
- Chưa gọi Groq thật hoặc đánh giá chất lượng câu trả lời LLM vì thiếu API key. Chế độ dev trả kết quả database thật; không giả lập model để tuyên bố hoàn thành.
- Chưa chạy trên MySQL 8, chưa kiểm chứng FULLTEXT ngram trên MySQL. MariaDB hiện dùng FULLTEXT thường và LIKE dự phòng theo skill.
- Đã kiểm tra trang HTML/JS được server phục vụ và HTTP đúng định dạng; chưa kiểm thử trình duyệt tự động.
- Pipeline hiện tại dùng truy vấn cố định có tham số cho các câu hỏi phổ biến; chưa nối LLM sinh SQL tùy ý.
- Opportunity/Quote/Booking chưa có schema; endpoint giữ HTTP 501. Quyền đọc đơn riêng của customer chưa được tự thêm.
- `.env` chứa cấu hình cục bộ và không được commit. Các file skill/tài nguyên và thay đổi `.env.example` do người dùng cung cấp được giữ nguyên.

Timeout MariaDB dùng `max_statement_time` theo [tài liệu MariaDB](https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/query-optimizations/aborting-statements).
