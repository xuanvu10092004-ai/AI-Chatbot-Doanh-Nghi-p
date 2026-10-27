# Phase 3 RAG Evaluation

| Metric | Trạng thái |
|---|---|
| Retrieval relevance | BLOCKED |
| Citation/source correctness | BLOCKED |
| Groundedness | BLOCKED |
| Hallucination check | BLOCKED |
| No-evidence refusal | NOT_RUN |

Nguyên nhân: chạy RAG qua Flask cần session/audit và tài liệu fixture. Không dùng tài liệu nghiệp vụ thật làm ground truth và không tự tạo PASS.
