USE honda_chatbot;
CREATE TABLE IF NOT EXISTS document_uploads (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 uploaded_by INT NOT NULL, category_id INT NOT NULL, branch_id INT NULL,
 title VARCHAR(255) NOT NULL, original_name VARCHAR(255) NOT NULL,
 stored_name VARCHAR(80) NOT NULL, file_format VARCHAR(10) NOT NULL,
 size_bytes INT NOT NULL, sha256 CHAR(64) NOT NULL,
 status ENUM('uploaded','processing','ready','needs_review','failed','published') NOT NULL DEFAULT 'uploaded',
 result_json JSON NULL, review_content LONGTEXT NULL, review_notes TEXT NULL,
 error_code VARCHAR(60) NULL, error_message VARCHAR(500) NULL,
 reviewed_by INT NULL, reviewed_at DATETIME NULL, published_doc_id INT NULL,
 version INT NOT NULL DEFAULT 1,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 processing_started_at DATETIME NULL,
 INDEX ix_document_owner(uploaded_by,created_at), INDEX ix_document_branch(branch_id,status),
 FOREIGN KEY(uploaded_by) REFERENCES users(id), FOREIGN KEY(category_id) REFERENCES kb_categories(id),
 FOREIGN KEY(branch_id) REFERENCES branches(id), FOREIGN KEY(reviewed_by) REFERENCES users(id),
 FOREIGN KEY(published_doc_id) REFERENCES kb_documents(id)
) COMMENT='Tài liệu tải lên và bản nháp trích xuất; chỉ bản đã duyệt mới vào kho tri thức';

INSERT INTO permissions(code,description)
SELECT 'document:manage','Tải lên, xem, hiệu đính và duyệt tài liệu trong phạm vi được cấp'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='document:manage');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,CASE WHEN r.name='branch_manager' THEN 'branch' ELSE 'all' END
FROM roles r JOIN permissions p ON p.code='document:manage'
WHERE r.name IN ('super_admin','branch_manager')
 AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id=r.id AND rp.permission_id=p.id);
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
SELECT 'documents','Tài liệu','/documents',p.id,85,TRUE FROM permissions p
WHERE p.code='document:manage' AND NOT EXISTS (SELECT 1 FROM nav_items WHERE code='documents');
