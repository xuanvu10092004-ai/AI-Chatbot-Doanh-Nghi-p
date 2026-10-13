"""Chuẩn hóa tiếng Việt và cách viết tên xe, không suy đoán thông số xe."""
import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFD', text.casefold().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', text).strip()


FAMILIES = (
    (r'\b(?:air\s*blade|ab)\b', 'Air Blade'),
    (r'\bsh\s*mode\b|\bshmode\b', 'SH Mode'),
    (r'\bsh\b', 'SH'), (r'\bvision\b', 'Vision'),
    (r'\blead\b', 'Lead'), (r'\bvario\b', 'Vario'),
    (r'\bfuture\b', 'Future'), (r'\bwave(?:\s+alpha)?\b', 'Wave'),
    (r'\bwinner(?:\s+x)?\b', 'Winner'), (r'\bblade\b', 'Blade'),
    (r'\brebel\b', 'Rebel'),
)


def product_pattern(question: str) -> str | None:
    q = normalize(question)
    # AB125, SH160i, shmode125 -> tên họ xe + dung tích người dùng yêu cầu.
    q = re.sub(r'([a-z])(?=\d)', r'\1 ', q)
    for expression, family in FAMILIES:
        match = re.search(expression, q)
        if match:
            engine = re.match(r'\s*(\d{2,3})(i|\s*fi)?\b', q[match.end():])
            return '%' + family + ('%' + engine.group(1) + '%' if engine else '%')
    return None


def wants_sql(question: str) -> bool:
    q = normalize(question)
    return product_pattern(question) is not None or any(term in q for term in (
        'so sanh', 'phan khuc', 'danh sach xe', 'xe duoi', 'xe tren',
        'gia re', 'dat nhat', 're nhat', 'bao nhieu', 'thong ke',
        'xe ga', 'tay ga', 'xe so', 'xe con',
    ))


def resolve_followup(question: str, history: list[dict]) -> str:
    q = normalize(question)
    if product_pattern(question) or not any(w in q for w in ('mau nao', 'mau gi', 'phien ban', 'ban abs', 'xe nay', 'gia bao nhieu', 'thong so', 'bao hanh')):
        return question
    for message in reversed(history):
        if message['sender'] != 'user':
            continue
        pattern = product_pattern(message['content'])
        if pattern:
            model = pattern.strip('%').replace('%', ' ')
            return question + ' (mẫu xe đang trao đổi: ' + model + ')'
    return question
