USE honda_chatbot;
INSERT INTO permissions(code,description)
SELECT 'invoice:export','Xuất chứng từ bán hàng PDF mô phỏng từ đơn được phép xem'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='invoice:export');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,CASE WHEN r.name IN ('super_admin','accountant') THEN 'all' ELSE 'branch' END
FROM roles r JOIN permissions p ON p.code='invoice:export'
WHERE r.name IN ('super_admin','accountant','branch_manager','sales_staff')
AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id=r.id AND rp.permission_id=p.id);
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
SELECT 'sales-orders','Đơn hàng / Xuất hóa đơn','/orders',p.id,55,TRUE FROM permissions p
WHERE p.code='order:read' AND NOT EXISTS (SELECT 1 FROM nav_items WHERE code='sales-orders');
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
SELECT 'quick-customer','Thêm nhanh khách mua xe','/customer-input?quick=1',p.id,54,TRUE FROM permissions p
WHERE p.code='customer:write' AND NOT EXISTS (SELECT 1 FROM nav_items WHERE code='quick-customer');
