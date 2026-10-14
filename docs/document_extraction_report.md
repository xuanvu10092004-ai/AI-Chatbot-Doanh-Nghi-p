# Báo cáo trích xuất tài liệu - 14/10/2026

Bộ mẫu tổng hợp có đáp án độc lập trong `data/samples/documents/manifest.json`. Recall văn bản = số token trong đáp án thu hồi được / tổng token đáp án; precision = số token đúng / tổng token trích xuất, bỏ khác biệt xuống dòng. Chỉ so phần văn bản, bảng đo riêng bằng tỷ lệ ô khớp chính xác và kích thước bảng. Thứ tự hai cột PDF và thứ tự đoạn/bảng DOCX được kiểm tra riêng bằng pytest. Đây là kết quả trên mẫu kiểm soát, không phải cam kết cho file thực tế và không phải độ chính xác OCR.

| File mẫu | Recall chữ | Precision chữ | Ô bảng đúng | Kết quả / trạng thái |
|---|---:|---:|---:|---|
| text.pdf | 100.0% | 100.0% | Không đo | Đã trích xuất |
| table.pdf | 100.0% | 100.0% | 100.0% | Đã trích xuất |
| columns.pdf | 100.0% | 100.0% | Không đo | Cần kiểm tra |
| scan.pdf | Không đo | Không đo | Không đo | Cần kiểm tra; scan_or_empty |
| mixed.pdf | 100.0% | 100.0% | Không đo | Cần kiểm tra; mixed |
| encrypted.pdf | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: unreadable_file |
| large.pdf | 100.0% | 100.0% | Không đo | Đã trích xuất |
| too_many_pages.pdf | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: page_limit |
| table.docx | 100.0% | 100.0% | 100.0% | Đã trích xuất |
| merged.docx | Không đo | Không đo | Không đo | Cần kiểm tra |
| table.xlsx | Không đo | Không đo | 100.0% | Cần kiểm tra |
| formula.xlsx | Không đo | Không đo | Không đo | Cần kiểm tra |
| large.xlsx | Không đo | Không đo | Không đo | Cần kiểm tra; 2001 dòng |
| too_many_rows.xlsx | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: cell_limit |
| corrupt.pdf | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: unreadable_file |
| wrong_extension.pdf | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: format_mismatch |
| corrupt.docx | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: corrupt_file |
| empty.xlsx | Không đo | Không đo | Không đo | Đúng lỗi kỳ vọng: file_size |

## Giới hạn và cách xử lý

- Chưa tích hợp OCR tự động. PDF scan/mờ/lệch được giữ file gốc, báo phần thiếu và cần nhập bản đã kiểm tra; không tạo chữ hay điểm tin cậy giả. PDF không có chữ có thể là trang trắng hoặc scan, không khẳng định chắc chắn là scan.
- PDF: bảng có đường kẻ được kiểm tra; bảng không đường kẻ, ô gộp, chữ xoay, font lỗi và bố cục hơn hai cột có thể không phục hồi đúng. Tách hai cột là heuristic, luôn có cảnh báo kiểm tra thứ tự.
- DOCX: giữ thứ tự đoạn/bảng cấp ngoài cùng, đọc header/footer. Bảng lồng, ô gộp, ảnh, textbox và footnote có giới hạn; không phục dựng bố cục trang hay theo dõi sửa đổi.
- XLSX: không chạy công thức/macro/liên kết ngoài. Công thức dùng cache sẵn có; thiếu cache thì đánh dấu ô thiếu, không thay bằng 0. Cache có thể cũ. Ô gộp chỉ lưu ô đầu; sheet ẩn được nêu rõ. Không phục dựng biểu đồ hay định dạng số tiền theo từng ô.
- Giới hạn: 10 MB/file, PDF 200 trang, XLSX 50 sheet, 10.000 dòng/200 cột mỗi sheet; tổng 50.000 ô và 200.000 ký tự. Không cắt im lặng khi vượt giới hạn. Subprocess đọc file có timeout 45 giây; không có giới hạn RAM cứng trên Windows.
- Nội dung đưa vào kho tri thức tối đa 60.000 byte UTF-8 theo cột TEXT hiện có. Tài liệu lớn phải chia nhỏ/hiệu đính; không tự ghi các dòng trích xuất vào sản phẩm, khách hàng hoặc đơn hàng.
- File đúng đuôi vẫn phải qua kiểm tra chữ ký và cấu trúc Office; chặn macro, ZIP giải nén quá lớn, nén bất thường, file rỗng và định dạng cũ. File PDF mã hóa/hỏng bị lỗi, không ghi vào kho tri thức.
- Bản nháp/metadata khác với dữ liệu đã công bố. Title, category, branch scope, content, xác nhận đối chiếu và phiên bản hiện hành phải hợp lệ; thiếu thì không ghi kb_documents. Mọi bản trích xuất phải được người dùng duyệt trước xuất bản.

## Tái tạo

`python -m pip install -r requirements-dev.txt`, `python scripts/generate_document_samples.py`, `python -m pytest -q tests/test_document_parser.py tests/test_document_uploads.py`, `python scripts/report_document_accuracy.py`.

API thư viện được đối chiếu với [pdfplumber](https://github.com/jsvine/pdfplumber), [python-docx](https://python-docx.readthedocs.io/en/latest/_modules/docx/document.html) và [openpyxl](https://openpyxl.readthedocs.io/en/stable/optimized.html).
