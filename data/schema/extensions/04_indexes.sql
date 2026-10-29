-- Tạo chỉ mục phục vụ tìm kiếm tài liệu RAG và tra cứu đơn hàng.
USE honda_chatbot;

-- Tạo FULLTEXT index cho RAG bằng ngram; kiểm tra trước để chạy lại không lỗi.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'kb_documents'
      AND INDEX_NAME = 'ft_kb_documents_title_content'
);
SET @sql = IF(
    @index_exists = 0,
    IF(VERSION() LIKE '%MariaDB%',
       'ALTER TABLE kb_documents ADD FULLTEXT INDEX ft_kb_documents_title_content (title, content)',
       'ALTER TABLE kb_documents ADD FULLTEXT INDEX ft_kb_documents_title_content (title, content) WITH PARSER ngram'),
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index lọc đơn hàng theo khách hàng.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND INDEX_NAME = 'idx_orders_customer_id'
);
SET @sql = IF(
    @index_exists = 0,
    'CREATE INDEX idx_orders_customer_id ON orders (customer_id)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index lọc đơn hàng theo chi nhánh và trạng thái.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND INDEX_NAME = 'idx_orders_branch_status'
);
SET @sql = IF(
    @index_exists = 0,
    'CREATE INDEX idx_orders_branch_status ON orders (branch_id, status)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
