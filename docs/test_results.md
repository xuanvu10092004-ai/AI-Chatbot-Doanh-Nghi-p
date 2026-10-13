# Kết quả kiểm thử chatbot Honda

Ngày kiểm chứng: 13/10/2026. Python 3.13, MariaDB 10.4.32 (XAMPP), Groq `openai/gpt-oss-20b`.

## Kết quả cuối

```text
python -m pytest -q
96 passed in 5.74s
```

Không skip test. Bao gồm MySQL thật và năm test gọi Groq thật với sản phẩm/tồn kho/tài liệu public. Người dùng đã cho phép các payload kiểm thử này sau khi kiểm tra phê duyệt tự động ban đầu chặn gửi schema ra ngoài.

`python init_db.py --extensions-only` chạy thành công hai lần; products=10, product_variants=28, inventory=84, users id>100=80, customer_profiles=80, orders=30. Không reset database, không sửa bảng chuẩn. `node --check static/script.js` và `git diff --check` đạt.

## Lỗi trong ảnh và kiểm chứng HTTP thật

| Trường hợp | Nguyên nhân trước sửa | Kết quả sau sửa |
|---|---|---|
| Guest hỏi tồn kho | UI không gửi danh tính, backend dùng guest | Tiếp tục từ chối đúng quyền; UI dev có lựa chọn tài khoản |
| Sales user 3 hỏi “hàng tồn kho còn bao nhiêu” | Truy vấn đếm dòng thay vì cộng số xe | HTTP 200, tổng số xe NT01 = 154, tính bằng SQL |
| “giá ab 125 bao nhiêu” | Không nhận diện AB và nhầm thành COUNT phiên bản | HTTP 200, không có dữ liệu; không đổi thành Air Blade 160 |
| “giá ab 160 bao nhiêu” | Tên viết tắt không được hiểu, LLM từng làm mất chữ số | HTTP 200, giá 56.500.000 / 57.500.000 / 60.500.000 VNĐ, renderer giữ đủ chữ số |
| “thông tin sh mode 125” | Chuyển sai sang RAG | HTTP 200, lấy đúng mẫu, phiên bản và thông số từ view |
| “xe ga dưới 50 triệu” | Định tuyến RAG sai; bind nhiều literal có lỗi thứ tự và tên tham số | HTTP 200, engine=groq-sql, chỉ kết quả xe ga hợp lệ từ SQL |
| “so sánh Vision 110 và Lead 125” | Không có truy vấn so sánh | HTTP 200, engine=groq-sql, kết quả SQL thực, không để LLM viết lại số |
| “màu nào?” sau câu hỏi SH Mode | Không mang tên xe sang lượt tiếp | Test đạt; cùng phiên và đúng mẫu đang hỏi |

## Nhóm test

- Alias có dấu/không dấu/viết liền, mười mẫu xe từ catalog thật; không thay AB125 bằng AB160.
- Giá khác số phiên bản; tồn kho cộng quantity; lọc NT01/NT02 và reset scope trong pool.
- UI dev hiển thị tài khoản thử nghiệm, production ẩn và bỏ qua header demo.
- Validator AST chặn bảng gốc, view trái quyền, CTE/subquery nguy hiểm, biến phiên và hàm nguy hiểm.
- Literal LLM được bind theo đúng thứ tự SQL; kiểm tra hơn 10 tham số tránh lỗi tên p1/p10.
- SQL renderer bảo toàn tiền, NLG không được viết lại số liệu SQL.
- Schema cho Groq chỉ chứa view được phép theo user và intent; câu SQL trái quyền bị chặn trước khi chạy và audit denied.
- History/session, audit, nguồn RAG, thiếu bằng chứng, lỗi kết nối có kiểm soát.
- Groq thật: hai test trả lời từ sản phẩm/public, ba test sinh SELECT cho ngân sách, nhóm tồn kho và so sánh giá; kết quả so với SQL trực tiếp.

## Mười câu chuẩn

Các giá trị dưới đây lấy từ truy vấn SQL thật trên bảng gốc, không gõ đáp án tay. Backend được đối chiếu bằng test tự động.

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

## File thêm/sửa của đợt nâng cấp

- Thêm `question_language.py`, `query_planner.py`, `llm_sql.py`, `answer_renderer.py`.
- Thêm `data/schema/extensions/05_ai_product_details.sql`, `tests/test_question_upgrade.py`, `tests/test_groq_queries.py`.
- Sửa `query_plans.py`, `sql_service.py`, `sql_safety.py`, `access_control.py`, `routing.py`, `app.py`.
- Sửa `templates/index.html`, `static/script.js`, `pytest.ini`, `README.md`, báo cáo này.

## Giới hạn

- Không bảo đảm mọi câu hỏi bất kỳ đều trả được: chỉ dữ liệu và tài liệu đã nạp, trong quyền người dùng. Câu mơ hồ cần làm rõ; thiếu dữ liệu không bịa.
- Không reset database theo giới hạn giữ dữ liệu. Chưa kiểm chứng MySQL 8/ngram, hiện kiểm chứng MariaDB.
- Opportunity/Quote/Booking chưa có schema; giữ HTTP 501. Chưa tự thêm quyền đọc đơn riêng của customer.
- UI đã kiểm tra HTML được phục vụ và JavaScript hợp lệ; chưa kiểm thử tương tác bằng trình duyệt tự động.
- `.env` không commit. Các thay đổi `.env.example`, `SKILL.md`, `assets/`, `references/` đã có từ người dùng được giữ nguyên.
