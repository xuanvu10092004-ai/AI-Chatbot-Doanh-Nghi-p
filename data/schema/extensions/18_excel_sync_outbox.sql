USE honda_chatbot;
CREATE TABLE IF NOT EXISTS excel_sync_changes (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, table_name VARCHAR(64) NOT NULL, operation VARCHAR(16) NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), processed_at DATETIME(6) NULL,
 INDEX ix_excel_pending(processed_at,id)
) ENGINE=InnoDB COMMENT='Outbox giao dịch; chỉ ACK chính xác các event đã thấy trong snapshot xuất';
CREATE TABLE IF NOT EXISTS excel_sync_state (
 id TINYINT PRIMARY KEY, status VARCHAR(16) NOT NULL DEFAULT 'pending',
 last_change_id BIGINT NOT NULL DEFAULT 0, last_success_at DATETIME NULL,
 last_worker_at DATETIME NULL, last_error VARCHAR(500) NULL, attempts INT NOT NULL DEFAULT 0,
 next_retry_at DATETIME NULL, output_path VARCHAR(1000) NULL
) ENGINE=InnoDB COMMENT='Trạng thái worker và lần xuất thành công; watermark không dùng để bỏ qua event chưa ACK';
INSERT IGNORE INTO excel_sync_state(id) VALUES(1);
INSERT IGNORE INTO excel_sync_changes(id,table_name,operation) VALUES(1,'bootstrap','snapshot');
DROP TRIGGER IF EXISTS tr_excel_users_insert;
CREATE TRIGGER tr_excel_users_insert AFTER INSERT ON users FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('users','insert');
DROP TRIGGER IF EXISTS tr_excel_users_update;
CREATE TRIGGER tr_excel_users_update AFTER UPDATE ON users FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('users','update');
DROP TRIGGER IF EXISTS tr_excel_users_delete;
CREATE TRIGGER tr_excel_users_delete AFTER DELETE ON users FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('users','delete');
DROP TRIGGER IF EXISTS tr_excel_customer_profiles_insert;
CREATE TRIGGER tr_excel_customer_profiles_insert AFTER INSERT ON customer_profiles FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_profiles','insert');
DROP TRIGGER IF EXISTS tr_excel_customer_profiles_update;
CREATE TRIGGER tr_excel_customer_profiles_update AFTER UPDATE ON customer_profiles FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_profiles','update');
DROP TRIGGER IF EXISTS tr_excel_customer_profiles_delete;
CREATE TRIGGER tr_excel_customer_profiles_delete AFTER DELETE ON customer_profiles FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_profiles','delete');
DROP TRIGGER IF EXISTS tr_excel_products_insert;
CREATE TRIGGER tr_excel_products_insert AFTER INSERT ON products FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('products','insert');
DROP TRIGGER IF EXISTS tr_excel_products_update;
CREATE TRIGGER tr_excel_products_update AFTER UPDATE ON products FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('products','update');
DROP TRIGGER IF EXISTS tr_excel_products_delete;
CREATE TRIGGER tr_excel_products_delete AFTER DELETE ON products FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('products','delete');
DROP TRIGGER IF EXISTS tr_excel_product_variants_insert;
CREATE TRIGGER tr_excel_product_variants_insert AFTER INSERT ON product_variants FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_variants','insert');
DROP TRIGGER IF EXISTS tr_excel_product_variants_update;
CREATE TRIGGER tr_excel_product_variants_update AFTER UPDATE ON product_variants FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_variants','update');
DROP TRIGGER IF EXISTS tr_excel_product_variants_delete;
CREATE TRIGGER tr_excel_product_variants_delete AFTER DELETE ON product_variants FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_variants','delete');
DROP TRIGGER IF EXISTS tr_excel_product_specs_insert;
CREATE TRIGGER tr_excel_product_specs_insert AFTER INSERT ON product_specs FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_specs','insert');
DROP TRIGGER IF EXISTS tr_excel_product_specs_update;
CREATE TRIGGER tr_excel_product_specs_update AFTER UPDATE ON product_specs FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_specs','update');
DROP TRIGGER IF EXISTS tr_excel_product_specs_delete;
CREATE TRIGGER tr_excel_product_specs_delete AFTER DELETE ON product_specs FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('product_specs','delete');
DROP TRIGGER IF EXISTS tr_excel_inventory_insert;
CREATE TRIGGER tr_excel_inventory_insert AFTER INSERT ON inventory FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('inventory','insert');
DROP TRIGGER IF EXISTS tr_excel_inventory_update;
CREATE TRIGGER tr_excel_inventory_update AFTER UPDATE ON inventory FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('inventory','update');
DROP TRIGGER IF EXISTS tr_excel_inventory_delete;
CREATE TRIGGER tr_excel_inventory_delete AFTER DELETE ON inventory FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('inventory','delete');
DROP TRIGGER IF EXISTS tr_excel_orders_insert;
CREATE TRIGGER tr_excel_orders_insert AFTER INSERT ON orders FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('orders','insert');
DROP TRIGGER IF EXISTS tr_excel_orders_update;
CREATE TRIGGER tr_excel_orders_update AFTER UPDATE ON orders FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('orders','update');
DROP TRIGGER IF EXISTS tr_excel_orders_delete;
CREATE TRIGGER tr_excel_orders_delete AFTER DELETE ON orders FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('orders','delete');
DROP TRIGGER IF EXISTS tr_excel_order_items_insert;
CREATE TRIGGER tr_excel_order_items_insert AFTER INSERT ON order_items FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('order_items','insert');
DROP TRIGGER IF EXISTS tr_excel_order_items_update;
CREATE TRIGGER tr_excel_order_items_update AFTER UPDATE ON order_items FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('order_items','update');
DROP TRIGGER IF EXISTS tr_excel_order_items_delete;
CREATE TRIGGER tr_excel_order_items_delete AFTER DELETE ON order_items FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('order_items','delete');
DROP TRIGGER IF EXISTS tr_excel_branches_insert;
CREATE TRIGGER tr_excel_branches_insert AFTER INSERT ON branches FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('branches','insert');
DROP TRIGGER IF EXISTS tr_excel_branches_update;
CREATE TRIGGER tr_excel_branches_update AFTER UPDATE ON branches FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('branches','update');
DROP TRIGGER IF EXISTS tr_excel_branches_delete;
CREATE TRIGGER tr_excel_branches_delete AFTER DELETE ON branches FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('branches','delete');
DROP TRIGGER IF EXISTS tr_excel_customer_admin_state_insert;
CREATE TRIGGER tr_excel_customer_admin_state_insert AFTER INSERT ON customer_admin_state FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_admin_state','insert');
DROP TRIGGER IF EXISTS tr_excel_customer_admin_state_update;
CREATE TRIGGER tr_excel_customer_admin_state_update AFTER UPDATE ON customer_admin_state FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_admin_state','update');
DROP TRIGGER IF EXISTS tr_excel_customer_admin_state_delete;
CREATE TRIGGER tr_excel_customer_admin_state_delete AFTER DELETE ON customer_admin_state FOR EACH ROW
 INSERT INTO excel_sync_changes(table_name,operation) VALUES('customer_admin_state','delete');
DROP TRIGGER IF EXISTS tr_customer_version_users_insert;
CREATE TRIGGER tr_customer_version_users_insert AFTER INSERT ON users FOR EACH ROW
 INSERT INTO customer_admin_state(customer_id) SELECT NEW.id WHERE NEW.user_type='customer'
 ON DUPLICATE KEY UPDATE version=version+1;
DROP TRIGGER IF EXISTS tr_customer_version_users_update;
CREATE TRIGGER tr_customer_version_users_update AFTER UPDATE ON users FOR EACH ROW
 INSERT INTO customer_admin_state(customer_id) SELECT NEW.id WHERE NEW.user_type='customer'
 ON DUPLICATE KEY UPDATE version=version+1;
DROP TRIGGER IF EXISTS tr_customer_version_customer_profiles_insert;
CREATE TRIGGER tr_customer_version_customer_profiles_insert AFTER INSERT ON customer_profiles FOR EACH ROW
 INSERT INTO customer_admin_state(customer_id) SELECT NEW.user_id
 ON DUPLICATE KEY UPDATE version=version+1;
DROP TRIGGER IF EXISTS tr_customer_version_customer_profiles_update;
CREATE TRIGGER tr_customer_version_customer_profiles_update AFTER UPDATE ON customer_profiles FOR EACH ROW
 INSERT INTO customer_admin_state(customer_id) SELECT NEW.user_id
 ON DUPLICATE KEY UPDATE version=version+1;
DROP TRIGGER IF EXISTS tr_customer_version_customer_profiles_delete;
CREATE TRIGGER tr_customer_version_customer_profiles_delete AFTER DELETE ON customer_profiles FOR EACH ROW
 INSERT INTO customer_admin_state(customer_id) SELECT OLD.user_id
 ON DUPLICATE KEY UPDATE version=version+1;

