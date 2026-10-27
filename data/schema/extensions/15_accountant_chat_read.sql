-- Bổ sung quyền đọc nghiệp vụ cho kế toán dùng chatbot tra cứu.
-- Chỉ thêm mapping role-permission, không thay đổi bảng chuẩn hoặc cấp quyền ghi.
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('inventory:read', 'customer:read')
WHERE r.name = 'accountant';