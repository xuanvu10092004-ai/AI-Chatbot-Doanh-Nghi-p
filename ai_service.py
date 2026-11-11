# ==========================================================
# Tên file: ai_service.py
# Mục đích của file: Tầng dịch vụ giao tiếp với Groq AI LLM (Large Language Model)
# File này dùng để làm gì:
#   - Khởi tạo kết nối tới Groq Cloud API sử dụng API Key bảo mật từ file môi trường (.env).
#   - Nhận câu hỏi từ người dùng và dữ liệu ngữ cảnh (context - từ SQL hoặc RAG document).
#   - Ghép ngữ cảnh vào Prompt (lời mồi) và gửi tới model Groq AI (mặc định Llama 3.3 70B).
#   - Trả về câu trả lời bằng tiếng Việt tự nhiên, ngắn gọn và chính xác cho giao diện người dùng.
# Khi nào file được gọi:
#   - Được gọi bởi app.py trong route POST /chat sau khi dữ liệu context đã được chuẩn bị bởi sql_service.py hoặc rag_service.py.
#   - Được gọi bởi test_sql.py và test_ai.py để kiểm tra kết quả sinh câu trả lời của AI.
# Luồng hoạt động tổng quát:
#   [Câu hỏi + Context từ SQL/RAG]
#           ↓
#   [Ghép Prompt cấu trúc cho LLM]
#           ↓
#   [Gọi Groq Chat Completions API (Llama-3.3-70b)]
#           ↓
#   [Trích xuất phản hồi văn bản tiếng Việt]
#           ↓
#   [Trả về cho Controller (app.py / test script)]
# ==========================================================

import os
from pathlib import Path
from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq

# ---------------------------------------------------------
# Bước 1: Nạp cấu hình từ biến môi trường
# - Bước này đang làm gì: Đọc file .env tại thư mục gốc dự án.
# - Vì sao cần bước me: Bảo mật API Key, không hardcode thông tin nhạy cảm vào mã nguồn.
# - Dữ liệu đi từ đâu đến đâu: Đọc từ file .env vào hệ thống os.environ của Python.
# - Sau bước này chương trình sẽ làm gì tiếp: Lấy API Key và Model name từ os.getenv.
# ---------------------------------------------------------
load_dotenv(Path(__file__).resolve().with_name(".env"))

# ---------------------------------------------------------
# Bước 2: Khai báo các hằng số cấu hình hệ thống AI
# - API_KEY: Khóa xác thực tài khoản Groq Cloud.
# - MODEL: Tên mô hình ngôn ngữ lớn (LLM) được sử dụng (Llama 3.3 70B Versatile).
# ---------------------------------------------------------
API_KEY = os.getenv("GROQ_API_KEY")
MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

class AIConfigurationError(RuntimeError):
    """Raised when required LLM configuration is missing."""


class AIServiceError(RuntimeError):
    def __init__(self, message, error_code, provider_status=None):
        super().__init__(message)
        self.error_code = error_code
        self.provider_status = provider_status


# ==========================================================
# Hàm generate_answer:
# - Hàm dùng để làm gì: Gửi prompt đã ghép context tới Groq AI và nhận câu trả lời dạng văn bản tiếng Việt.
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc của người dùng.
#     + context (str): Dữ liệu ngữ cảnh (bản ghi từ SQLite hoặc văn bản từ RAG documents).
# - Giá trị trả về:
#     + str: Câu trả lời tự nhiên bằng tiếng Việt do mô hình AI sinh ra.
# - Hàm này được gọi ở đâu:
#     + app.py (trong hàm chat())
#     + test_sql.py (trong hàm test_pipeline())
#     + test_ai.py (trong hàm test_with_real_data())
# - Vai trò trong hệ thống: Tầng tổng hợp ngôn ngữ tự nhiên cuối cùng (NLG - Natural Language Generation).
# ==========================================================
def generate_answer(question, context):
    """
    Sinh câu trả lời từ Groq AI dựa trên câu hỏi và ngữ cảnh.

    Args:
        question (str): Câu hỏi từ người dùng.
        context  (str): Dữ liệu/ngữ cảnh liên quan lấy từ database.

    Returns:
        str: Câu trả lời bằng tiếng Việt từ model AI.
    """

    # ---------------------------------------------------------
    # Bước 1 trong hàm: Xây dựng Prompt (Lập trình lời mồi)
    # - Bước này đang làm gì: Định hình vai trò trợ lý AI, đưa dữ liệu context và câu hỏi người dùng vào khung template.
    # - Vì sao cần bước này: Giúp LLM hiểu rõ vai trò, giới hạn phạm vi trả lời chỉ dựa trên dữ liệu được cung cấp.
    # - Dữ liệu đi từ đâu đến đâu: Biến context và question được nhúng vào chuỗi f-string prompt.
    # - Sau bước này chương trình sẽ làm gì tiếp: Gửi chuỗi prompt này tới API của Groq.
    # ---------------------------------------------------------
    prompt = f"""Bạn là trợ lý AI hỗ trợ quản lý doanh nghiệp.

Dựa vào dữ liệu bên dưới để trả lời câu hỏi. Không tự tạo số liệu, tên người,
trạng thái hoặc chính sách không có trong dữ liệu.
Nếu dữ liệu ghi rõ không tìm thấy tài liệu hoặc không có truy vấn phù hợp,
hãy nói rõ chưa có bằng chứng/dữ liệu trong hệ thống và không suy đoán.
Nếu người dùng chỉ chào hỏi hoặc hỏi trợ lý có thể giúp gì, hãy đáp lại thân thiện
và nêu ngắn gọn các chức năng doanh nghiệp của chatbot.

Dữ liệu:
{context}

Câu hỏi:
{question}

Trả lời ngắn gọn, dễ hiểu bằng tiếng Việt."""

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Gọi Groq API Chat Completion
    # - Bước này đang làm gì: Thực hiện HTTP POST request tới server Groq.
    # - Vì sao cần bước này: Nhờ siêu máy chủ AI phân tích ngữ cảnh và sinh văn bản tự nhiên.
    # - Ý nghĩa tham số:
    #     + model: Tên mô hình AI (llama-3.3-70b-versatile)
    #     + messages: Danh sách hội thoại gửi đi (role="user")
    #     + temperature=0.3: Giảm độ ngẫu nhiên, giúp AI trả lời bám sát dữ liệu thực tế, ít "chém gió".
    #     + max_tokens=1024: Tối đa 1024 token văn bản phản hồi.
    # - Dữ liệu đi từ đâu đến đâu: Gửi prompt lên Groq API -> Nhận đối tượng response từ Groq.
    # - Sau bước này chương trình sẽ làm gì tiếp: Trích xuất đoạn text trả lời từ object response.
    # ---------------------------------------------------------
    if not API_KEY:
        raise AIConfigurationError(
            "Chưa cấu hình GROQ_API_KEY. Hãy thêm khóa vào file .env."
        )

    client = Groq(api_key=API_KEY, timeout=30.0, max_retries=1)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1024,
        )
    except APITimeoutError as exc:
        raise AIServiceError(
            "Groq không phản hồi trong thời gian chờ. Vui lòng thử lại.",
            "provider_timeout",
        ) from exc
    except APIConnectionError as exc:
        raise AIServiceError(
            "Không thể kết nối tới Groq. Vui lòng kiểm tra mạng và thử lại.",
            "provider_unavailable",
        ) from exc
    except APIStatusError as exc:
        if exc.status_code in (401, 403):
            message = "Groq từ chối xác thực. Hãy kiểm tra GROQ_API_KEY."
            code = "provider_authentication"
        elif exc.status_code == 429:
            message = "Groq đang giới hạn yêu cầu. Vui lòng thử lại sau."
            code = "provider_rate_limited"
        else:
            message = "Groq không xử lý được yêu cầu. Vui lòng thử lại."
            code = "provider_error"
        raise AIServiceError(
            message,
            code,
            provider_status=exc.status_code,
        ) from exc

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Trích xuất nội dung văn bản và trả về
    # - Bước này đang làm gì: Lấy chuỗi text ở vị trí lựa chọn đầu tiên response.choices[0].message.content.
    # - Vì sao cần bước này: Bỏ bớt các thông tin metadata (token count, finish_reason...) chỉ giữ lại câu trả lời.
    # - Dữ liệu đi từ đâu đến đâu: Từ object response -> Trả về chuỗi str cho hàm gọi.
    # ---------------------------------------------------------
    if not response.choices or not response.choices[0].message.content:
        raise AIServiceError(
            "Groq trả về phản hồi rỗng. Vui lòng thử lại.",
            "empty_provider_response",
        )
    return response.choices[0].message.content.strip()