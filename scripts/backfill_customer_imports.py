# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Khôi phục liên kết lịch sử nhập file từ kết quả commit cũ, không tạo lại khách."""
import json  # Đọc hoặc ghi dữ liệu JSON trong luồng xử lý của file.


# Khôi phục liên kết dòng khách từ batch đã commit; INSERT IGNORE giúp chạy lặp an toàn.
def backfill(connection):
    count=0
    with connection.cursor(dictionary=True) as cur:
        cur.execute("SELECT id,result_json,preview_json FROM customer_input_batches WHERE status='committed' AND document_id IS NOT NULL AND result_json IS NOT NULL")
        batches=cur.fetchall()
        for batch in batches:
            result=json.loads(batch['result_json']);preview=json.loads(batch['preview_json'] or '[]')
            ids=result.get('customer_ids',[])
            if len(ids)!=len(preview):
                raise RuntimeError('Lịch sử nhập file không khớp số dòng; cần kiểm tra batch #'+str(batch['id']))
            for item,customer in zip(preview,ids):
                cur.execute('''INSERT IGNORE INTO customer_import_rows(batch_id,customer_id,row_number,action)
                            SELECT %s,u.id,%s,%s FROM users u WHERE u.id=%s AND u.user_type='customer' ''',
                            (batch['id'],item['row'],item['action'],customer))
                count+=cur.rowcount
    connection.commit()
    return count
