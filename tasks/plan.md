# Trợ lý hội thoại nghiệp vụ

Giữ nguyên UI/API hiện có và các thay đổi đã stage. Không đồng bộ upstream (đang chậm 3 commit), không reset MySQL dùng chung.

1. M1: resolver xác định trước, LLM chỉ chọn công cụ được cấp; trạng thái server theo phiên/chủ sở hữu, hỏi lại khi thiếu/đa nghĩa. Kiểm tra paraphrase, kiểu tham số, nhiều lượt, không ghi khi chưa xác nhận.
2. M2: lookup entity có scope, nối các service còn thiếu, đủ 10 widget; giữ hợp đồng draft/batch và kiểm tra version. Kiểm tra RBAC, scope, rollback, replay.
3. M3: điều phối đọc/ghi và điều kiện, hybrid retrieval có nguồn, kết quả số giữ nguyên từ DB. Kiểm tra yêu cầu hỗn hợp và tài liệu chưa công bố.
4. M4: bổ sung chọn entity, hỏi lại và liên kết trên chat; giữ các nút/trang. Chạy test tập trung rồi toàn bộ trên MariaDB riêng, ghi kết quả thật.

Kiểm thử ghi chỉ chạy trên tiến trình MariaDB riêng với bản sao database; không dùng runner reset/restore database dùng chung. Từng phần được commit riêng, không đưa hai file đã stage của người dùng vào commit.
