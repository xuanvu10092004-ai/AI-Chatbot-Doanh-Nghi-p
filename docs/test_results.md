# Ket qua kiem thu Honda AI Chatbot

Ngay ghi nhan gan nhat: **13/10/2026**.

## Tong hop

| Nhom | Ket qua | Ghi chu |
|---|---:|---|
| Validator SQL | Dat | 8 passed, khong can MySQL |
| Groq API | Skip | Thieu `GROQ_API_KEY` |
| MySQL/RBAC | Blocked | MySQL tu choi ket noi `127.0.0.1:3306` |
| Parser/OCR/RAG da dinh dang | Chua chay | Hang muc tuan 05-07 |
| Hoi quy 6 module | Mot phan | CRM/Warehouse/AI Chat co nen tang; Opportunity/Quote/Booking con phu thuoc schema-extension |

## Bo cau hoi chuan

Dap an tinh bang SQL truc tiep trong `tests/test_honda_mysql.py`, khong hardcode. Chua the chay do MySQL chua kha dung.

| # | Cau hoi | View/dieu kien ky vong | Ket qua |
|---:|---|---|---|
| 1 | SH 160i gia bao nhieu? | `v_ai_products` theo `model_name` | Blocked |
| 2 | Gia niem yet SH 160i | `MIN(list_price)` tu `v_ai_products` | Blocked |
| 3 | Co bao nhieu phien ban xe? | `COUNT(*)` tu `v_ai_products` | Blocked |
| 4 | Co bao nhieu san pham trong kho? | `COUNT(*)` tu `v_ai_inventory` | Blocked |
| 5 | Ton kho tai NT01 | `branch_code = 'NT01'` | Blocked |
| 6 | Co bao nhieu khach hang? | `COUNT(*)` tu `v_ai_customers` | Blocked |
| 7 | Co bao nhieu khach hang da mua? | `customer_status = 'Da mua'` | Blocked |
| 8 | Co bao nhieu don hang? | `COUNT(DISTINCT order_id)` tu `v_ai_orders` | Blocked |
| 9 | Don hang tai NT02 | `branch_code = 'NT02'` | Blocked |
| 10 | Cac mau xe tay ga | `segment = 'tay_ga'` | Blocked |

## Ca quyen can chay lai khi MySQL hoat dong

- Guest hoi gia von: `denied` va co audit.
- Sales user 3 hoi ton kho: `allowed` trong pham vi duoc cap.
- Ky thuat vien user 5 hoi gia von: `denied`.
- Guest doc tai lieu danh muc sales: `denied`.
- User co `scope_branch_id` khong doc duoc chi nhanh ngoai pham vi.

## Kiem chung tiep theo

1. Khoi dong MySQL va tao `.env` hop le, khong ghi mat khau vao repository.
2. Chay `python init_db.py --reset` de ap dung schema, view, user doc va index.
3. Chay `python -m pytest -q` va cap nhat bang nay bang ket qua thuc te.
4. Bo sung test PDF/DOCX/XLSX, OCR, preview-confirm-save, RAG co nguon va hoi quy 6 module theo tuan 05-10.