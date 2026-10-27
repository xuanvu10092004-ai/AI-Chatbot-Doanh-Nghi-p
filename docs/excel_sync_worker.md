# Khách hàng admin-only và worker MySQL → Excel

MySQL là nguồn dữ liệu chính. Export chính thức: `data/exports/honda_chatbot_synced.xlsx`. File `data/source/honda_dataset_khach_hang_san_pham.xlsx` chỉ là template/đầu vào, không còn bị exporter hoặc trang GET ghi đè.

## Triển khai không reset dữ liệu dùng chung

Tạm dừng ghi trong lúc cài trigger lần đầu; chỉ chạy trên máy triển khai với `.env` đúng server dùng chung. Không sửa `.env` hoặc chạy `--reset` trên server dùng chung.

```powershell
python init_db.py --extension 17_customer_admin.sql
python init_db.py --extension 18_excel_sync_outbox.sql
python excel_sync_worker.py --once --force
python app.py
```

Extension 17 chỉ thêm permission, metadata/version/xóa mềm và view active. Extension 18 thêm journal/state và trigger. Các trigger chỉ ghi DB, cùng transaction với INSERT/UPDATE/DELETE; không đọc/ghi Excel. Không chạy lại extension 18 khi đang có giao dịch ghi vì việc thay định nghĩa trigger cần cửa sổ bảo trì. Không dùng `--extensions-only` để thay thế nếu chỉ muốn hai migration này (chế độ cũ còn chạy các bước seed/account khác).

`customer:admin:manage` dành riêng cho super_admin toàn hệ thống. Backend kiểm tra cả permission hiệu lực, loại tài khoản staff và vai trò super_admin chưa hết hạn; cấp nhầm permission cho role khác vẫn không mở quyền. Staff giữ quyền tạo khách mới. Excel/import/batch/chat không được sửa khách đã có nếu người thao tác không phải admin. Admin account editor không sửa thông tin hồ sơ khách qua đường vòng; dùng trang Khách hàng để có version check.

Admin có nút Sửa/Xóa ở `/customers`, ô xem khách đã xóa và nút Khôi phục. PATCH dùng version; DELETE/restore cần `confirmed:true`. API: GET/PATCH/DELETE `/api/customers/<id>`, POST `/api/customers/<id>/restore`. Xóa mềm không xóa orders, order_items, hóa đơn, lịch sử hoặc audit. Khách đã xóa không nằm trong active lists/dashboard/AI/customer lookup/export và không được đăng nhập; khôi phục giữ trạng thái tài khoản trước đó.

Chat: `Sửa khách hàng #101: Số điện thoại: 0901234567`, `Xóa khách hàng #101`, `Khôi phục khách hàng #101`. Có thể dùng tên/mã KH thật; tên trùng phải chọn, không đoán ID. Mỗi thao tác cần bản xem trước và xác nhận. Dùng ID thực tế trong môi trường của bạn.

## Chạy độc lập với website/trình duyệt

Chọn **một máy Windows** làm máy xuất chính thức, có Python/dependencies và quyền ghi `data/exports/`. Worker dùng cùng `db.py`/`.env` với ứng dụng (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`); không dùng account chatbot_ro và không cần credential mới. Khi dùng LAN, DB_HOST phải là địa chỉ MySQL chung, không phải loopback của máy thành viên. MySQL không cần nằm cùng máy với worker.

```powershell
python excel_sync_worker.py --interval 2
```

Worker polling mỗi 2 giây, gom tối đa 10.000 event đã commit vào một lần xuất. Tất cả sheet đọc trong cùng REPEATABLE READ snapshot. Khóa MySQL GET_LOCK theo database giữ độc quyền giữa các process/máy; khóa tự giải phóng khi process chết. File tạm cùng thư mục được kiểm ZIP, sheet/số dòng rồi replace nguyên tử; Excel đang mở/khóa file thì giữ bản cũ và retry. Việc xuất không nằm trong transaction ghi nghiệp vụ; lỗi Excel không đổi một lần lưu DB thành lỗi.

Sau thành công, chỉ các ID journal thực sự thấy trong snapshot được ACK. Watermark để quan sát, không dùng `id > watermark` lọc hàng chờ, tránh mất event có ID nhỏ nhưng commit muộn. Crash sau replace trước ACK sẽ xuất lại an toàn. Retry giữ trong MySQL, backoff 2–256 giây; restart không cần state bộ nhớ. Dữ liệu đã rollback không có event để worker thấy.

Các bảng theo dõi: users, customer_profiles, products, product_variants, product_specs, inventory, orders, order_items, branches và customer_admin_state. TRUNCATE/tắt trigger không thuộc luồng INSERT/UPDATE/DELETE được hỗ trợ; sau thay đổi quản trị như vậy chạy `--once --force`.

## Tự khởi động khi đăng nhập Windows

Từ PowerShell của tài khoản Windows sẽ vận hành worker:

```powershell
.\scripts\install_excel_sync_task.ps1 -Python 'C:\duong-dan-Python\pythonw.exe'
Get-ScheduledTask -TaskName PortalExcelSync
Get-ScheduledTaskInfo -TaskName PortalExcelSync
```

Thay đường dẫn bằng `pythonw.exe` của môi trường đã cài requirements (có thể trong `.venv\Scripts`). Script đăng ký AtLogOn cho tài khoản hiện tại, chạy pythonw không mở cửa sổ, không chạy nhiều instance, restart khi lỗi và không giới hạn thời gian chạy; đồng thời khởi động task. Máy/tài khoản phải duy trì phiên Windows cho cấu hình này. Nếu cần chạy trước khi đăng nhập hoặc sau logout, quản trị Windows cấu hình task “Run whether user is logged on or not” với tài khoản có quyền đọc `.env` và ghi export; không đặt mật khẩu Windows trong source.

Không chạy worker ở mọi máy thành viên: mỗi máy có thư mục local riêng và chỉ một máy được chỉ định sở hữu file xuất chính thức. Muốn mọi máy mở cùng file, chia sẻ thư mục export từ máy đó theo chính sách LAN. Website và chatbot có thể đóng; chỉ cần MySQL và worker tiếp tục chạy.

Nếu đang chạy worker thủ công, dừng tiến trình đó trước khi chuyển sang Scheduled Task để chỉ duy trì một worker. Phiên triển khai hiện tại lưu PID của worker pythonw tại `data/exports/excel_sync_worker.pid`; kiểm tra đúng PID/tiến trình trước khi dừng. Việc khởi động lại web app là riêng biệt, cần làm để nạp quyền/giao diện mới nếu app đã chạy từ code cũ.

## Quan sát và phục hồi

- Trang Khách hàng của admin tự đọc trạng thái qua GET `/api/excel-sync`: pending/running/completed/failed, số event chờ, lỗi, số lần thử, lần thành công/heartbeat gần nhất và watermark. GET không chạy export.
- Nhật ký xoay vòng: `data/exports/excel_sync_worker.log` (3 bản × 2 MB). `last_success_at` cũ hoặc chưa có heartbeat nghĩa là cần kiểm tra worker/task; lưu DB thành công không đồng nghĩa Excel đã cập nhật.
- Khi Excel khóa file: đóng file và chờ retry. Có thể chạy `python excel_sync_worker.py --once --force` để kiểm tra ngay. Exit 1 khi thất bại; busy/idle không ghi file và không làm mất event.
- Dừng task: `Stop-ScheduledTask -TaskName PortalExcelSync`. Chạy lại: `Start-ScheduledTask -TaskName PortalExcelSync`. Không xóa journal/state để “sửa” lỗi.
- Event đã ACK được giữ cho đối soát. DBA có thể lưu trữ/dọn riêng các hàng `processed_at IS NOT NULL` theo chính sách lưu trữ; không dọn hàng chưa ACK.

## Kiểm thử an toàn

```powershell
python -X utf8 scripts/test_isolated_mysql.py --seed tests/test_customer_admin.py tests/test_excel_sync_worker.py tests/test_customer_admin_browser.py
python -X utf8 scripts/test_isolated_mysql.py --seed --tb=short
```

Runner tạo MariaDB/workspace riêng, chỉ reset fixture riêng và kiểm tra hash các bảng nguồn không đổi. Workbook template trong workspace thử được chuẩn bị từ seed để kiểm tra round-trip/import; exporter production không làm việc này. Snapshot/export kiểm thử có dữ liệu riêng tư, nằm trong `data/exports/` bị Git bỏ qua.
