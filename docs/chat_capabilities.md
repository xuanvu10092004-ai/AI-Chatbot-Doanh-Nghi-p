# Khả năng hội thoại và backend

| Trang/API hiện có | Service/handler kiểm quyền | Công cụ chat |
|---|---|---|
| `/catalog`, `/api/catalog` | `save_vehicle`, version đời xe | `catalog_list`, `catalog_save` |
| Tra giá/thông số | `answer_sql_question`, AST + chatbot_ro | `product_search`, câu hỏi SQL |
| `/inventory` | `records`, scope inventory:read | `inventory_search`, câu hỏi SQL |
| `/stock-receipts` | `receive_stock`, `list_receipts` | `stock_receive`, `stock_list` |
| `/customers` | `records`, scope customer:read | `customer_search`, câu hỏi SQL |
| `/customer-input` | `customer_chat`, stage/revise/commit | `customer_input`, lệnh thêm/sửa khách cũ |
| `/api/chat/customer-file` | `upload_document`, `stage_document` | nút đính kèm khách; `customer_imports` |
| `/orders` | `sales_orders_list` | `orders_list`, câu hỏi SQL |
| `/api/orders/<id>/invoice.pdf` | `sales_invoice_export`, scope kép | `invoice_export` |
| `/bookings` | create/update_booking + version | `booking_create/list/update` |
| `/api/appointments` | appointment_service + owner/branch | `appointment_create/list/update` |
| `/dashboard` (10 widget) | `widget_data`, quyền riêng từng widget | `dashboard_read`, widget theo tháng/chi nhánh/nguồn/trạng thái/bán chạy/lợi nhuận |
| `/documents`, API file/process/review/publish | document_service + category/branch/version | `document_upload` mở trang tải lên; `documents_list`, `document_detail/process/review/publish` |
| `/admin/users` | admin_service, scope + RBAC version | `users_list`, `user_save/password`, `assignment_save/delete` |
| `/admin/roles`, `/admin/permissions` | admin_service, scope all | `roles_list/save/delete`, `permissions_list`, `permission_save` |
| `/admin/audit` | scope audit:read | `audit_list` |
| Tài liệu tri thức đã công bố | `search_documents`, v_user_kb_access | câu hỏi RAG kèm nguồn |

Mọi lệnh ghi tạo bản nháp hoặc dùng batch khách hiện có, phải xác nhận trước khi service thực thi. File tải lên vẫn đi qua biểu mẫu và nút xác nhận hiện có; không tạo đường dẫn file từ nội dung LLM.

Trạng thái theo phiên/chủ sở hữu, có thời hạn 30 phút; tên trùng yêu cầu chọn entity. Quy trình nhiều bước được kiểm quyền trước bước đầu, từng thao tác ghi xác nhận riêng. Điều kiện tồn một SP/chi nhánh được giữ cùng draft và kiểm tra lại dưới khóa lúc confirm, kể cả sau bổ sung/sửa tham số. Điều kiện khác hỏi lại. Excel được xuất sau commit, bỏ callback khi rollback savepoint.

Chưa có backend: tạo báo giá, cơ hội; duyệt đơn/thanh toán/giao xe. Chỉ có tra cứu đơn và PDF mô phỏng. Chat không báo thành công cho các thao tác này. Login/logout/đổi mật khẩu cá nhân tiếp tục dùng biểu mẫu bảo mật, không đưa mật khẩu vào hội thoại.
