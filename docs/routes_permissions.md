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
| /api/bookings | GET,POST | kb:public:read | all / branch / own according to permission |
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
| /bookings | GET | kb:public:read | all / branch / own according to permission |
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
