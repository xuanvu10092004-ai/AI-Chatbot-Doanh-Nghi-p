USE honda_chatbot;

-- Placeholder bắt buộc được init_db.py thay từ CHATBOT_RO_PASSWORD trong .env.
-- File này không chứa mật khẩu thật.
CREATE USER IF NOT EXISTS 'chatbot_ro'@'%' IDENTIFIED BY '__CHATBOT_RO_PASSWORD__';
ALTER USER 'chatbot_ro'@'%' IDENTIFIED BY '__CHATBOT_RO_PASSWORD__';

GRANT SELECT ON honda_chatbot.v_ai_products TO 'chatbot_ro'@'%';
GRANT SELECT ON honda_chatbot.v_ai_inventory TO 'chatbot_ro'@'%';
GRANT SELECT ON honda_chatbot.v_ai_customers TO 'chatbot_ro'@'%';
GRANT SELECT ON honda_chatbot.v_ai_orders TO 'chatbot_ro'@'%';
GRANT SELECT ON honda_chatbot.v_ai_product_costs TO 'chatbot_ro'@'%';
