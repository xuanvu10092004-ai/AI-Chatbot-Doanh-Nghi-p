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
