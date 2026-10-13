USE honda_chatbot;
CREATE OR REPLACE FUNCTION fn_session_user() RETURNS INT NOT DETERMINISTIC NO SQL RETURN @ai_user;
CREATE OR REPLACE VIEW v_ai_customers AS
SELECT u.id AS customer_id,u.email,u.full_name,u.phone,u.user_type,u.home_branch_id,u.home_branch_id AS branch_id,
 b.code AS home_branch_code,b.name AS home_branch_name,cp.customer_code,cp.gender,cp.birth_date,cp.province,cp.district,cp.address,cp.occupation,cp.lead_source,cp.interested_product_id,cp.payment_preference,cp.registered_at,cp.status AS customer_status
FROM users u JOIN customer_profiles cp ON cp.user_id=u.id LEFT JOIN branches b ON b.id=u.home_branch_id
WHERE u.user_type='customer' AND (fn_session_branch() IS NULL OR u.home_branch_id=fn_session_branch())
 AND (fn_session_user() IS NULL OR u.id=fn_session_user());
CREATE OR REPLACE VIEW v_ai_orders AS
SELECT o.id AS order_id,o.customer_id,u.full_name AS customer_name,o.branch_id,b.code AS branch_code,b.name AS branch_name,
 oi.variant_id,p.id AS product_id,p.model_name,pv.variant_name,SUBSTRING_INDEX(pv.variant_name,' - ',-1) AS color,
 oi.quantity,oi.unit_price,oi.quantity*oi.unit_price AS line_amount,o.discount_amount,
 oi.quantity*oi.unit_price-o.discount_amount AS net_amount,o.status,o.created_at
FROM orders o JOIN users u ON u.id=o.customer_id JOIN branches b ON b.id=o.branch_id
JOIN order_items oi ON oi.order_id=o.id JOIN product_variants pv ON pv.id=oi.variant_id JOIN products p ON p.id=pv.product_id
WHERE (fn_session_branch() IS NULL OR o.branch_id=fn_session_branch()) AND (fn_session_user() IS NULL OR o.customer_id=fn_session_user());
GRANT EXECUTE ON FUNCTION honda_chatbot.fn_session_user TO 'chatbot_ro'@'localhost';
