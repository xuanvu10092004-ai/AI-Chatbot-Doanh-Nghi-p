# Bao cao du an: AI Chatbot Doanh Nghiep

## 1. Tong quan

De tai ke thua va nang cap he thong AI CRM/RAG trong 12 tuan, tu **12/10/2026 den 03/01/2027**. Phien ban hien tai phuc vu du lieu Honda, ket hop Flask, MySQL, LLM va RAG de tra loi co can cu, co kiem soat quyen va co nhat ky truy xuat.

Muc tieu:

- Nang cap 6 module: CRM, Warehouse, Opportunity, Quote, Dashboard va AI Chat/RAG.
- Bo sung dang nhap, RBAC da cap va gioi han du lieu theo chi nhanh.
- Tiep nhan PDF, Word, Excel, anh/PDF scan; AI chi ghi du lieu sau preview, chinh sua va xac nhan.
- Xay dung RAG co nguon, khong tu khang dinh khi thieu bang chung.

## 2. Kien truc hien tai

Flask cung cap UI va API. `routing.py` phan biet cau hoi du lieu cau truc voi cau hoi tai lieu. Truoc khi truy xuat, he thong xac dinh intent, kiem tra RBAC/pham vi chi nhanh va ghi audit.

```text
Nguoi dung -> Flask API -> session -> intent + quyen
           -> SQL an toan hoac RAG co quyen -> context co nguon
           -> LLM -> cau tra loi -> audit/session/message
```

MySQL cung cap cac view `v_ai_products`, `v_ai_inventory`, `v_ai_customers`, `v_ai_orders`; `v_ai_product_costs` chi danh cho quyen `price:cost:read`. Khong dua `password_hash` vao context va khong cho LLM truy cap bang goc.

RBAC dung `roles`, `permissions`, `user_roles`, `role_permissions`, `v_user_permissions` va `v_user_kb_access`. Truy xuat bi tu choi phai tra thong bao chung, ghi `chatbot_audit_log` va khong xac nhan du lieu co ton tai.

RAG chi tim trong tap tai lieu duoc phep doc; guest chi thay danh muc public. Ket qua phai kem id va tieu de nguon. Tai lieu scan/anh di qua OCR, chuan hoa, preview, xac nhan roi moi ghi DB.

## 3. Ke hoach 12 tuan

| Tuan | Giai doan | Trong tam | Dau ra |
|---:|---|---|---|
| 01 | Khao sat | Kiem ke he thong, 6 module, loi va rui ro | Hien trang, backlog, test hoi quy |
| 02 | Kien truc | Du lieu, RBAC, tai lieu, ghi co kiem soat | So do, wireframe, quy uoc API |
| 03 | Dang nhap | Session/token va bao ve endpoint | Test truy cap trai quyen |
| 04 | Nguoi dung | Tai khoan, vai tro, quyen, audit | Vai tro mau chay o UI/API |
| 05 | Tai lieu | Upload va trich xuat PDF/DOCX/XLSX | Kiem tra dinh dang, dung luong, loi |
| 06 | OCR/nhap lieu | OCR, schema, preview-confirm-save | Log, canh bao thieu/khong chac chan |
| 07 | Kho tri thuc | Chunking, embedding, top-k, nguon | RAG co bang chung |
| 08 | Tich hop 3 module | Chat, CRM, Opportunity | End-to-end co quyen |
| 09 | Tich hop 3 module | Quote, Warehouse, Dashboard | Du 6 module co ban |
| 10 | Kiem thu | Tich hop, hoi quy, bao mat, tai file | Bao cao loi va trang thai |
| 11 | Dong goi | Demo, cau hinh, huong dan, bao cao, slide | Ban demo chay lai duoc |
| 12 | Nghiem thu | Sua loi, quay demo, ban giao | Ban phat hanh va ho so hoan chinh |

## 4. Phan cong va nghiem thu

- **Vu:** backend, database, API, xac thuc/RBAC, parsing/OCR, embedding/RAG, logging, test bao mat va phan ky thuat bao cao.
- **Thuong:** UI/UX, dang nhap, quan tri tai khoan, upload/preview, kho tri thuc, 6 module, test nguoi dung va trinh bay.
- **Phoi hop:** chot schema JSON, ma loi, quy tac quyen; moi chuc nang phai goi API that.

Nghiem thu khi backend kiem tra quyen, tai lieu da dinh dang co xu ly loi, du lieu AI co preview-confirm-save, RAG co nguon, 6 module co luong chinh, test co bao cao va cau hinh khong chua bi mat.

## 5. Gioi han

Opportunity, Quote va Booking con phu thuoc schema-extension chinh thuc; khong tu mo rong schema chuan. RAG da phuong thuc day du la hang muc mo rong, uu tien OCR va RAG tren noi dung da trich xuat.