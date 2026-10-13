# Ke hoach trien khai chi tiet: AI Chatbot Doanh Nghiep

Tieu tai lieu nay chuyen ke hoach trong `Ke_Hoach_Thuc_Tap.xlsx` thanh lo trinh ky thuat co dau ra kiem chung duoc. Thoi gian: **12/10/2026 - 03/01/2027**.

## 1. Nguyen tac

1. Ke thua 6 module, khong viet lai toan bo neu chua co ly do ky thuat.
2. Kiem tra quyen o backend/API, khong chi an nut tren giao dien.
3. Tach tiep nhan -> trich xuat -> xac thuc/duyet -> ghi DB.
4. RAG gioi han theo quyen, luu nguon va noi ro khi khong du bang chung.
5. Khong dua API key, mat khau hay du lieu nhay cam vao ma nguon/log.

## 2. Nen tang ky thuat

- Flask va MySQL Honda la nen tang chay hien tai.
- `schema_context.py` tao context tu metadata/comment cua `v_ai_*`.
- `sql_safety.py` chan SQL khong phai mot cau `SELECT`, view ngoai whitelist, comment, `SLEEP`, `INTO OUTFILE`; dong thoi gioi han dong/thoi gian.
- `db.py` tach pool ung dung va pool doc cho text-to-SQL.
- RBAC/audit dung `v_user_permissions`, `v_user_kb_access`, `chatbot_intents`, `chatbot_audit_log`.
- Test validator da co; test MySQL/RBAC can MySQL that.

## 3. Lo trinh theo tuan

### Tuan 01: Khao sat va chot pham vi

- **Vu:** ra soat backend, database, API, AI/RAG, dependency; ghi loi va rui ro.
- **Thuong:** ra soat giao dien, nghiep vu, tai tai lieu va man hinh nang cap.
- **Dau ra:** hien trang, backlog uu tien, danh sach giu/sua/bo sung va test hoi quy.

### Tuan 02: Thiet ke kien truc

- Thiet ke du lieu, RBAC, quy trinh tai lieu va co che ghi co kiem soat.
- **Vu:** API, users/roles/permissions, documents, extraction jobs/logs va lien ket nghiep vu.
- **Thuong:** wireframe dang nhap, quan tri tai khoan, upload, preview va kho tri thuc.
- **Dau ra:** so do, wireframe, quy uoc API va phan cong.

### Tuan 03-04: Dang nhap va nguoi dung

- **Vu:** API dang nhap/thoat, bam mat khau, session/token, middleware quyen va audit.
- **Thuong:** giao dien dang nhap, trang thai tai khoan, dieu huong, gan vai tro va thong bao loi.
- **Dau ra:** vai tro mau duoc test o ca UI va API; truy cap trai quyen bi tu choi.

### Tuan 05: Tiep nhan tai lieu

- Upload va trich xuat PDF co text, DOCX, XLSX.
- **Vu:** parser, chuan hoa, metadata, trang thai va loi file.
- **Thuong:** danh sach tai lieu, tien do, loi va preview.
- **Dau ra:** file mau duoc kiem tra dinh dang va dung luong.

### Tuan 06: OCR va AI nhap lieu

- OCR anh/PDF scan, anh xa schema, kiem tra truong bat buoc/kieu du lieu.
- Nguoi co quyen preview, sua va xac nhan truoc khi ghi DB; luu nguon, log, do khong chac chan.
- **Dau ra:** ban ghi cho duyet, khong ghi truc tiep du lieu khong hop le.

### Tuan 07: Kho tri thuc va RAG

- Chunking/embedding, luu vector, truy xuat top-k va ket noi LLM.
- Gioi han theo `v_user_kb_access`, tra id/tieu de/trang/doan neu co.
- **Dau ra:** cau tra loi co nguon; ca khong co bang chung phai noi ro.

### Tuan 08-09: Tich hop 6 module

- Tich hop Chat, CRM, Opportunity, Quote, Warehouse, Dashboard voi intent va quyen.
- AI chi ho tro thao tac; giao dich nhay cam phai co quyen va xac nhan.
- **Dau ra:** 6 module co luong co ban, khong ghi du lieu ngoai quy trinh.

### Tuan 10: Kiem thu va on dinh

- Test tich hop, hoi quy, RBAC, parser/OCR, RAG, tai file, du lieu sai va AI thieu chac chan.
- **Vu:** API, bao mat, du lieu bien, log, backup va phuc hoi.
- **Thuong:** end-to-end, responsive, thong bao loi va kha nang su dung.
- **Dau ra:** bao cao test, danh sach loi/trang thai, khong con loi nghiem trong.

### Tuan 11-12: Dong goi va nghiem thu

- Chuan hoa `.env`, huong dan chay, sao luu, kien truc, database, API, AI, anh va slide.
- Sua loi cuoi, quay demo, ra soat ma nguon/cau hinh/du lieu, ban giao.
- **Dau ra:** ban phat hanh, video demo, bao cao/slide, gioi han va huong phat trien.

## 4. Checklist nghiem thu

- [ ] Dang nhap va quyen duoc kiem tra o backend/API.
- [ ] PDF text, PDF scan/anh, Word va Excel co luong xu ly va bao loi.
- [ ] AI tao du lieu co preview, sua va xac nhan truoc ghi DB.
- [ ] RAG co nguon; thieu bang chung thi khong tu khang dinh.
- [ ] Sau nang cap, 6 module co luong chinh.
- [ ] Co bao cao test, huong dan chay, cau hinh khong chua API key va slide demo.