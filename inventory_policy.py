# Nhận diện câu hỏi về xe sắp hết hàng theo ngưỡng dùng chung.
from question_language import normalize  # Chuẩn hóa câu có dấu/không dấu trước khi so từ khóa.

LOW_STOCK_THRESHOLD = 5


def asks_low_stock(question):
    q = normalize(question)
    return any(term in q for term in ('sap het hang', 'sap het', 'gan het hang', 'ton thap'))
