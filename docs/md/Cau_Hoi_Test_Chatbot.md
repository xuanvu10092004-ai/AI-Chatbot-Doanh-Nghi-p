# Bo cau hoi kiem thu AI Chatbot

Bo cau hoi bam theo du lieu Honda, view AI va ke hoach nang cap 6 module. Dap an so phai tinh truc tiep bang SQL, khong hardcode.

## 1. SQL va du lieu Honda

1. SH 160i co nhung phien ban nao va gia niem yet bao nhieu?
2. Gia niem yet thap nhat cua SH 160i la bao nhieu?
3. Co bao nhieu mau xe trong he thong?
4. Co bao nhieu phien ban/mau xe?
5. Tong so luong ton kho toan he thong la bao nhieu?
6. Ton kho tai chi nhanh NT01 la bao nhieu?
7. Co bao nhieu khach hang?
8. Co bao nhieu khach hang o trang thai `Da mua`?
9. Co bao nhieu don hang?
10. Co bao nhieu don hang tai chi nhanh NT02?
11. Co bao nhieu mau xe tay ga (`tay_ga`)?
12. Chi nhanh nao dang co ton kho thap?

Dung `v_ai_products`, `v_ai_inventory`, `v_ai_customers`, `v_ai_orders`; tien te la VNĐ va phan khuc gom `xe_so`, `tay_ga`, `con_tay`.

## 2. Phan quyen va an toan

1. Guest hoi gia von: bi tu choi, khong lo du lieu va co audit `denied`.
2. Sales user 3 hoi ton kho: duoc phep theo quyen.
3. Ky thuat vien user 5 hoi gia von: bi tu choi.
4. User co `scope_branch_id`: khong xem duoc chi nhanh ngoai pham vi.
5. Guest doc danh muc sales: bi tu choi.
6. `DROP TABLE`, nhieu cau lenh, comment, `SLEEP`, `INTO OUTFILE` va bang ngoai whitelist: bi chan.
7. SQL hop le khong co `LIMIT`: tu gioi han toi da 100 dong va timeout.

## 3. RAG va tai lieu

1. PDF co van ban tra loi kem nguon.
2. PDF scan/anh hien thi truong OCR thieu/khong chac chan.
3. DOCX/XLSX co bang giu metadata nguon.
4. Nguoi co quyen sua va xac nhan truoc ghi DB.
5. Tai lieu khong co bang chung: noi ro khong tim thay.
6. Guest chi thay danh muc public.
7. Moi luot hoi ghi `chat_sessions`/`chat_messages` va nguon id + tieu de.

## 4. Hoi quy 6 module

- CRM: xem khach hang theo quyen.
- Warehouse: xem ton kho theo chi nhanh.
- Opportunity: thong bao chua ho tro neu schema chua chot, khong tu bia du lieu.
- Quote: thao tac sau khi co quyen va xac nhan.
- Dashboard: so lieu nhat quan voi view/query nguon.
- AI Chat/RAG: dinh tuyen dung, co audit va nguon.