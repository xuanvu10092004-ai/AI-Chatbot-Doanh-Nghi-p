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
    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"  // Báo cho server biết body là JSON
        },
        body: JSON.stringify({ question: question })  // Chuyển object JS -> chuỗi JSON
    })
        // Khi nhận được response, parse JSON
        .then(response => response.json())

        // Khi parse xong, hiển thị câu trả lời từ AI lên giao diện
        .then(data => {
            // Tạo bong bóng tin nhắn bot (màu xám, căn trái)
            const botMessage = document.createElement("div");
            botMessage.className = "bot-message";
            botMessage.innerText = data.answer;  // Nội dung trả về từ backend
            chatMessages.appendChild(botMessage);

            // Tự động cuộn xuống cuối khu vực chat để hiện tin nhắn mới nhất
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })

        // Xử lý lỗi mạng hoặc lỗi server (ví dụ: không kết nối được)
        .catch(error => {
            const errorMessage = document.createElement("div");
            errorMessage.className = "bot-message";
            errorMessage.innerText = "Có lỗi xảy ra khi gửi câu hỏi.";
            chatMessages.appendChild(errorMessage);
        });

    // Xóa nội dung ô input sau khi gửi để người dùng nhập câu tiếp theo
    input.value = "";
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