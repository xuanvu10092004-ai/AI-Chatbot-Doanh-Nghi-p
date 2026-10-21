-- Mở rộng view sản phẩm AI với đời xe và trạng thái vòng đời.
USE honda_chatbot;
CREATE OR REPLACE VIEW v_ai_products AS
SELECT p.id AS product_id,p.model_name,pv.id AS variant_id,pv.variant_name,
 SUBSTRING_INDEX(pv.variant_name,' - ',-1) AS color,p.segment,p.engine_cc,pv.list_price,
 COALESCE((SELECT SUM(i.quantity) FROM inventory i WHERE i.variant_id=pv.id),0) AS total_stock,
 p.fuel_consumption_l100km,p.description,ps.engine_type,ps.fuel_tank_l,ps.weight_kg,ps.brake_type,ps.warranty,
 r.model_year,COALESCE(r.lifecycle,'current') AS lifecycle
FROM products p JOIN product_variants pv ON pv.product_id=p.id
LEFT JOIN product_specs ps ON ps.product_id=p.id
-- Cập nhật từ điển dữ liệu để mô hình hiểu các trường bổ sung.
LEFT JOIN vehicle_releases r ON r.variant_id=pv.id;
INSERT INTO ai_data_dictionary(view_name,column_name,description_vi) VALUES
 ('v_ai_products','model_year','Năm đời xe; NULL là chưa cập nhật, không tự suy đoán năm'),
 ('v_ai_products','lifecycle','current = đời hiện hành; previous = đời trước; discontinued = ngừng kinh doanh')
ON DUPLICATE KEY UPDATE description_vi=VALUES(description_vi);
