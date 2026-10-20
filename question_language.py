"""Chuẩn hóa câu hỏi và nhận diện mẫu xe/tồn kho."""
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
    (r'\badv\b', 'ADV'), (r'\brebel\b', 'Rebel'),
)


def product_patterns(question: str) -> list[str]:
    q = re.sub(r'([a-z])(?=\d)', r'\1 ', normalize(question))
    matches = []
    for expression, family in FAMILIES:
        for match in re.finditer(expression, q):
            engine = re.match(r'\s*(\d{2,3})(i|\s*fi)?\b', q[match.end():])
            pattern = '%' + family + ('%' + engine.group(1) + '%' if engine else '%')
            matches.append((match.start(), match.end(), pattern))
    patterns, end = [], -1
    for start, stop, pattern in sorted(matches, key=lambda item: (item[0], -item[1])):
        if start < end:
            continue
        end = stop
        if pattern not in patterns:
            patterns.append(pattern)
    return patterns


def product_pattern(question: str) -> str | None:
    patterns = product_patterns(question)
    return patterns[0] if patterns else None


def asks_available_stock(question: str) -> bool:
    q = normalize(question)
    pattern = product_pattern(question)
    return bool(
        re.search(r'\bcon (?:hang|xe)\b', q)
        or re.search(r'\b(?:chi nhanh|dai ly|cua hang|o dau)\b.*\b(?:con|co xe)\b', q)
        or (pattern and re.search(r'\bcon(?: hang| xe| khong|\s*[?!.,]*$)', q))
        or (pattern and re.search(r'\bkho\b.*\b(?:co|con|het|may|bao nhieu)\b', q))
    )


def wants_sql(question: str) -> bool:
    q = normalize(question)
    return product_pattern(question) is not None or any(term in q for term in (
        'so sanh', 'phan khuc', 'danh sach xe', 'xe duoi', 'xe tren',
        'gia re', 'dat nhat', 're nhat', 'bao nhieu', 'thong ke',
        'xe ga', 'tay ga', 'xe so', 'xe con',
    ))


def resolve_followup(question: str, history: list[dict]) -> str:
    q = normalize(question)
    if any(term in q for term in ('het hang', 'tong ton', 'san pham nao', 'tat ca san pham')):
        return question
    if product_pattern(question) or not any(w in q for w in ('mau nao', 'mau gi', 'phien ban', 'ban abs', 'xe nay', 'gia bao nhieu', 'thong so', 'bao hanh', 'chi nhanh', 'dai ly', 'cua hang', 'o dau', 'con khong')):
        return question
    for message in reversed(history):
        if message['sender'] != 'user':
            continue
        pattern = product_pattern(message['content'])
        if pattern:
            model = pattern.strip('%').replace('%', ' ')
            return question + ' (mau xe dang trao doi: ' + model + ')'
    return question
