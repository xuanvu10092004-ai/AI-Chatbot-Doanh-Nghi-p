"""Quy ước tồn kho dùng chung cho chatbot và màn hình bán hàng."""
from question_language import normalize

LOW_STOCK_THRESHOLD = 5


def asks_low_stock(question):
    q = normalize(question)
    return any(term in q for term in ('sap het hang', 'sap het', 'gan het hang', 'ton thap'))
