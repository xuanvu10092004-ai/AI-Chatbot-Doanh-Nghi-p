# Routes, permissions and scope

| Route | Methods | Authorization | Data scope |
|---|---|---|---|
| / | GET | authenticated session | n/a |
| /admin/audit | GET | audit:read | all / branch / own according to permission |
| /admin/permissions | GET | rbac:manage | all only (global RBAC configuration) |
| /admin/roles | GET | rbac:manage | all only (global RBAC configuration) |
| /admin/users | GET | user:manage | all / branch / own according to permission |
| /api/admin/audit | GET | audit:read | all / branch / own according to permission |
| /api/admin/lookups | GET | user:manage | all / branch / own according to permission |
| /api/admin/permissions | GET | rbac:manage | all only (global RBAC configuration) |
| /api/admin/permissions/<int:target_id> | PUT | rbac:manage | all only (global RBAC configuration) |
| /api/admin/roles | GET | rbac:manage | all only (global RBAC configuration) |
| /api/admin/roles | POST | rbac:manage | all only (global RBAC configuration) |
| /api/admin/roles/<int:target_id> | DELETE,PUT | rbac:manage | all only (global RBAC configuration) |
| /api/admin/users | GET | user:manage | all / branch / own according to permission |
| /api/admin/users | POST | user:manage | all / branch / own according to permission |
| /api/admin/users/<int:target_id> | PUT | user:manage | all / branch / own according to permission |
| /api/admin/users/<int:target_id>/roles | DELETE,POST | user:manage | all / branch / own according to permission |
| /api/bookings | GET | booking:read | all / branch / own |
| /api/bookings | POST | booking:create | all / branch / own; kiểm tra khách và chi nhánh |
| /api/bookings/lookups | GET | booking:create | danh sách khách/chi nhánh trong scope |
| /api/bookings/<id> | PATCH | booking:read + booking:manage (xác nhận/hoàn tất), booking:create (hủy lịch của mình) | scope, version, trạng thái hợp lệ |
| /catalog | GET | product:manage | dữ liệu API yêu cầu scope all |
| /api/catalog | GET, POST | product:manage | chỉ all |
| /api/catalog/<id> | PUT | product:manage | chỉ all; kiểm tra version, audit |
| /api/customers | GET | customer:read | all / branch / own according to permission |
| /api/dashboard | GET | dashboard:view | all / branch / own according to permission |
| /api/dashboard/bestsellers | GET | order:read | all / branch / own according to permission |
| /api/dashboard/customer-source | GET | customer:read | all / branch / own according to permission |
| /api/dashboard/customer-status | GET | customer:read | all / branch / own according to permission |
| /api/dashboard/customers | GET | customer:read | all / branch / own according to permission |
| /api/dashboard/inventory | GET | inventory:read | all / branch / own according to permission |
| /api/dashboard/inventory-branch | GET | inventory:read | all / branch / own according to permission |
| /api/dashboard/orders | GET | order:read | all / branch / own according to permission |
| /api/dashboard/profit | GET | dashboard:finance, price:cost:read | all / branch / own according to permission |
| /api/dashboard/revenue-branch | GET | order:read | all / branch / own according to permission |
| /api/dashboard/revenue-month | GET | order:read | all / branch / own according to permission |
| /api/inventory | GET | inventory:read | all / branch / own according to permission |
| /api/low-stock | GET | inventory:read | all / branch / own according to permission |
| /api/opportunities | GET,POST | order:read | all / branch / own according to permission |
| /api/potential-customers | GET | customer:read | all / branch / own according to permission |
| /api/quotes | GET,POST | order:read | all / branch / own according to permission |
| /bookings | GET | booking:read | all / branch / own |
| /change-password | GET,POST | authenticated session | n/a |
| /chat | GET | kb:public:read | all / branch / own according to permission |
| /chat | POST | kb:public:read | all / branch / own according to permission |
| /customers | GET | customer:read | all / branch / own according to permission |
| /dashboard | GET | dashboard:view | all / branch / own according to permission |
| /guest | POST | public + CSRF | n/a |
| /inventory | GET | inventory:read | all / branch / own according to permission |
| /login | GET,POST | public + CSRF | n/a |
| /logout | POST | authenticated session | n/a |
| /opportunities | GET | order:read | all / branch / own according to permission |
| /quotes | GET | order:read | all / branch / own according to permission |
| /static/<path:filename> | GET | public asset | n/a |
