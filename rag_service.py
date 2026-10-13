from __future__ import annotations

import re

from access_control import authorize_intent, detect_intent
from db import cursor

MAX_DOCS = 3


def extract_keywords(question: str) -> list[str]:
    stopwords = {
        "là", "là gì", "gì", "như", "thế", "nào", "có", "không", "và",
        "của", "cho", "với", "được", "trong", "khi", "này", "đó", "các",
        "những", "một", "hay", "hoặc", "tôi", "bạn", "hãy", "cần", "muốn",
        "biết", "xem", "tìm", "về", "theo", "đến",
        "tài", "liệu", "thủ", "tục", "hướng", "dẫn", "chính", "sách",
    }
    words = [word for word in re.findall(r"[\wÀ-ỹ-]+", question.casefold()) if len(word) >= 3]
    return [word for word in words if word not in stopwords] or [question]


def _search_query(question: str, user_id: int | None, use_like: bool = False) -> tuple[str, tuple[object, ...]]:
    keywords = " ".join(extract_keywords(question))
    if use_like:
        words = extract_keywords(question)[:12]
        # Tất cả từ khóa là tham số; ký tự wildcard trong đầu vào được escape.
        values = tuple('%' + word.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%' for word in words)
        condition = ' OR '.join(["(d.title LIKE %s ESCAPE '!' OR d.content LIKE %s ESCAPE '!')"] * len(words))
        params = tuple(value for value in values for _ in range(2))
        if user_id is None:
            query = "SELECT DISTINCT d.id, d.title, d.content FROM kb_documents d JOIN kb_categories c ON c.id = d.category_id WHERE c.code = 'public' AND d.branch_id IS NULL"
        else:
            query = 'SELECT DISTINCT d.id, d.title, d.content FROM kb_documents d JOIN v_user_kb_access a ON a.doc_id = d.id WHERE a.user_id = %s'
            params = (user_id, *params)
        return query + ' AND (' + condition + ') ORDER BY d.id LIMIT %s', (*params, MAX_DOCS)
    if user_id is None:
        return (
            """
            SELECT d.id, d.title, d.content
            FROM kb_documents d
            JOIN kb_categories c ON c.id = d.category_id
            WHERE c.code = 'public'
              AND d.branch_id IS NULL
              AND MATCH(d.title, d.content) AGAINST (%s IN NATURAL LANGUAGE MODE)
            ORDER BY MATCH(d.title, d.content) AGAINST (%s IN NATURAL LANGUAGE MODE) DESC, d.id
            LIMIT %s
            """,
            (keywords, keywords, MAX_DOCS),
        )
    return (
        """
        SELECT DISTINCT d.id, d.title, d.content
        FROM kb_documents d
        JOIN v_user_kb_access access ON access.doc_id = d.id
        WHERE access.user_id = %s
          AND MATCH(d.title, d.content) AGAINST (%s IN NATURAL LANGUAGE MODE)
        ORDER BY MATCH(d.title, d.content) AGAINST (%s IN NATURAL LANGUAGE MODE) DESC, d.id
        LIMIT %s
        """,
        (user_id, keywords, keywords, MAX_DOCS),
    )


def search_documents(question: str, user_id: int | None = None, session_id: int | None = None) -> str:
    """Retrieve permission-filtered evidence and include document sources."""
    if session_id is None:
        raise ValueError("RAG cần session_id để ghi audit trước khi truy xuất")

    authorization = authorize_intent(session_id, user_id, detect_intent(question))
    if not authorization["allowed"]:
        return authorization["denied_message"]

    with cursor("app") as db_cursor:
        db_cursor.execute('SELECT VERSION() AS version')
        mariadb = 'MariaDB' in db_cursor.fetchone()['version']
        query, params = _search_query(question, user_id, use_like=mariadb)
        db_cursor.execute(query, params)
        documents = db_cursor.fetchall()

    if not documents:
        return "Không tìm thấy bằng chứng trong tài liệu được phép truy cập."

    context_parts = [f"Tìm thấy {len(documents)} nguồn bằng chứng:"]
    for document in documents:
        context_parts.append(
            f"[Nguồn id={document['id']} | tiêu đề={document['title']}]\n{document['content']}"
        )
    return "\n\n".join(context_parts)
