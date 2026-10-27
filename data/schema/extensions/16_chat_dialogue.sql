-- Trạng thái hội thoại thuộc phiên xác thực; không đổi schema nghiệp vụ chuẩn.
USE honda_chatbot;
CREATE TABLE IF NOT EXISTS chat_dialogue_state (
 session_id INT PRIMARY KEY,
 user_id INT NULL,
 payload JSON NOT NULL,
 version INT NOT NULL DEFAULT 1,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
 FOREIGN KEY(user_id) REFERENCES users(id)
) COMMENT='Ý định, tham số đang nhập, entity và draft của trợ lý; không chứa mật khẩu';
INSERT IGNORE INTO chatbot_intents(code,description,required_permission_id,data_source)
 SELECT CONCAT('tool_',v.name),v.description,p.id,'controlled_tool' FROM (
 SELECT 'product_search' name,'Tra sản phẩm và giá' description,'kb:public:read' perm
 UNION ALL SELECT 'inventory_search','Tra tồn kho','inventory:read'
 UNION ALL SELECT 'customer_search','Tra khách hàng','customer:read'
 UNION ALL SELECT 'customer_input','Bản nháp nhập khách hàng','customer:write'
 UNION ALL SELECT 'customer_imports','Lịch sử nhập khách','customer:read'
 UNION ALL SELECT 'document_detail','Đọc nội dung trích xuất','document:manage'
 UNION ALL SELECT 'document_process','Trích xuất lại tài liệu','document:manage'
 UNION ALL SELECT 'document_upload','Tải lên tài liệu có xác nhận','document:manage'
 ) v JOIN permissions p ON p.code=v.perm;
