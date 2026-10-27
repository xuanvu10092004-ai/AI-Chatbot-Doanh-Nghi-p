# Phase 3 Generalization

Đã chạy lại 30 câu paraphrase tại `data/ai_training/generalization.jsonl` sau khi sửa nguyên nhân gốc trong `routing.py`.

| Metric | Kết quả |
|---|---:|
| Route đúng trước khi sửa | 26/30 |
| Route đúng sau khi sửa | 30/30 |
| LLM calls | 0 |
| SQL/RAG answer correctness | NOT_RUN |

Bốn lỗi ban đầu do fallback mặc định câu ngắn sang RAG, intent `ask_price_list` chưa được ưu tiên thành SQL, và mẫu phủ định quyền chưa nhận diện ngôn ngữ tự nhiên. Đã sửa bằng heuristic có đối tượng, mapping intent nghiệp vụ và deny pattern có kiểm soát. Vì tập 30 câu đã giúp xác định lỗi, kết quả 30/30 là kiểm thử hồi quy trên cùng tập, không phải ước lượng độc lập mới. Đã bổ sung 4 biến thể tự nhiên vào test suite và tất cả đều đạt.