// ============================================================
// script.js - Logic xử lý giao diện chatbot
// Gửi câu hỏi đến backend Flask qua API /chat (POST),
// nhận câu trả lời và hiển thị lên màn hình.
// Hỗ trợ gửi bằng nút "Gửi" hoặc phím Enter.
// ============================================================


/**
 * Hàm chính: Gửi câu hỏi của người dùng đến backend và hiển thị câu trả lời.
 * Được gọi khi người dùng nhấn nút "Gửi" hoặc nhấn phím Enter.
 */
function sendQuestion() {
    // Lấy ô input và khu vực hiển thị tin nhắn từ DOM
    const input = document.getElementById("questionInput");
    const chatMessages = document.getElementById("chatMessages");
    const sendButton = document.getElementById("sendButton");

    // Lấy nội dung câu hỏi và loại bỏ khoảng trắng thừa hai đầu
    const question = input.value.trim();

    // Kiểm tra nếu người dùng chưa nhập gì thì hiện thông báo và dừng
    if (question === "") {
        alert("Vui lòng nhập câu hỏi!");
        return;
    }

    // ----------------------------------------------------------
    // Hiển thị tin nhắn của người dùng lên giao diện (bong bóng xanh, căn phải)
    // ----------------------------------------------------------
    const userMessage = document.createElement("div");
    userMessage.className = "user-message";   // CSS class định nghĩa trong style.css
    userMessage.innerText = question;
    chatMessages.appendChild(userMessage);

    // ----------------------------------------------------------
    // Gửi câu hỏi đến backend Flask qua HTTP POST /chat
    // Body là JSON: { "question": "..." }
    // ----------------------------------------------------------
    input.disabled = true;
    sendButton.disabled = true;
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
    })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.answer || "Máy chủ không xử lý được câu hỏi.");
            }
            if (typeof data.answer !== "string") {
                throw new Error("Phản hồi từ máy chủ không đúng định dạng.");
            }
            return data;
        })
        .then(data => appendBotMessage(data.answer))
        .catch(error => appendBotMessage(error.message || "Không thể kết nối tới máy chủ."))
        .finally(() => {
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
        });
}

function appendBotMessage(text) {
    const chatMessages = document.getElementById("chatMessages");
    const botMessage = document.createElement("div");
    botMessage.className = "bot-message";
    botMessage.innerText = text;
    chatMessages.appendChild(botMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// ----------------------------------------------------------
// Lắng nghe sự kiện nhấn phím trên ô input
// Nếu người dùng nhấn Enter -> gọi sendQuestion()
// event.preventDefault() ngăn không cho xuống dòng (default của Enter trong input)
// ----------------------------------------------------------
document.getElementById("questionInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Ngăn hành vi mặc định của phím Enter
        sendQuestion();
    }
});