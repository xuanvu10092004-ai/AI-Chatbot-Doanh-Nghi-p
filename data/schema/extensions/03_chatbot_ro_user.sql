-- Cấp quyền đọc giới hạn cho tài khoản kết nối text-to-SQL của chatbot.
USE honda_chatbot;
-- init_db.py tạo/cập nhật chatbot_ro@localhost bằng tham số từ .env.
-- Chỉ truy cập cục bộ; không đọc bảng gốc, không ghi.
GRANT SELECT ON honda_chatbot.v_ai_products TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot.v_ai_inventory TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot.v_ai_customers TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot.v_ai_orders TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot.v_ai_product_costs TO 'chatbot_ro'@'localhost';
GRANT EXECUTE ON FUNCTION honda_chatbot.fn_session_branch TO 'chatbot_ro'@'localhost';
