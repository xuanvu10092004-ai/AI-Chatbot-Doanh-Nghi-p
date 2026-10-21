# Chuẩn hóa dấu gạch trong nội dung hiển thị mà không sửa dữ liệu lưu trong CSDL.


# Thay en dash/em dash thành dấu gạch ngang thường ở ranh giới hiển thị.
def normalize_dashes(value: str) -> str:
    """Đổi gạch dài sang '-' kể cả khi chúng đến từ LLM hoặc dữ liệu cũ.

    Không sửa nội dung bảng trong CSDL: chuẩn hóa ở ranh giới hiển thị để
    giữ nguyên dữ liệu gốc và sử dụng cùng quy ước cho các câu trả lời sau này.
    """
    return value.replace('\u2014', '-').replace('\u2013', '-')
