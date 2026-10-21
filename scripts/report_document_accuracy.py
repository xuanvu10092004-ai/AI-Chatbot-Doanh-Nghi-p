# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Đo trên đáp án mẫu, không suy rộng thành độ chính xác mọi tài liệu/OCR."""
import json  # Đọc manifest đáp án mẫu và tạo báo cáo Markdown.
import re  # So sánh token văn bản, bỏ khác biệt xuống dòng.
import sys  # Thêm thư mục dự án vào đường dẫn import của Python.
from pathlib import Path  # Tìm mẫu tài liệu và ghi báo cáo tại thư mục dự án.
from collections import Counter  # Đếm token trùng để tính recall/precision.

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from document_parser import parse_document, ParseError  # Dùng parser và giới hạn xử lý file.


# So sánh kết quả parser với manifest độc lập, ghi bảng và trả trạng thái lỗi mẫu.
def report():
    root=Path(__file__).resolve().parents[1]
    samples=root/'data/samples/documents'
    cases=json.loads((samples/'manifest.json').read_text(encoding='utf-8'))
    lines=['# Báo cáo trích xuất tài liệu - 14/10/2026','',
           'Bộ mẫu tổng hợp có đáp án độc lập trong `data/samples/documents/manifest.json`. '
           'Recall văn bản = số token trong đáp án thu hồi được / tổng token đáp án; '
           'precision = số token đúng / tổng token trích xuất, bỏ khác biệt xuống dòng. '
           'Chỉ so phần văn bản, bảng đo riêng bằng tỷ lệ ô khớp chính xác và kích thước bảng. '
           'Thứ tự hai cột PDF và thứ tự đoạn/bảng DOCX được kiểm tra riêng bằng pytest. '
           'Đây là kết quả trên mẫu kiểm soát, không phải cam kết cho file thực tế và không phải độ chính xác OCR.','',
           '| File mẫu | Recall chữ | Precision chữ | Ô bảng đúng | Kết quả / trạng thái |',
           '|---|---:|---:|---:|---|']
    failures=[]
    for case in cases:
        try:
            result=parse_document(samples/case['file'])
            if 'error' in case:failures.append(case['file'])
            recall=precision=table_score='Không đo'
            if case.get('text'):
                gold=Counter(re.findall(r'\S+',case['text']))
                actual=Counter(re.findall(r'\S+','\n'.join(b['text'] for b in result['blocks'] if b['kind']=='text')))
                correct=sum((gold&actual).values())
                recall=f'{100*correct/sum(gold.values()):.1f}%';precision=f'{100*correct/max(1,sum(actual.values())):.1f}%'
            if case.get('tables'):
                actual=[b['rows'] for b in result['blocks'] if b['kind']=='table'];gold=case['tables']
                cells=sum(len(row) for table in gold for row in table)
                matches=sum(i<len(actual) and j<len(actual[i]) and k<len(actual[i][j]) and actual[i][j][k]==value
                            for i,table in enumerate(gold) for j,row in enumerate(table) for k,value in enumerate(row))
                actual_cells=sum(len(row) for table in actual for row in table)
                table_score=f'{100*matches/max(cells,actual_cells,1):.1f}%'
            outcome={'needs_review':'Cần kiểm tra','extracted':'Đã trích xuất'}[result['quality']['state']]
            if case.get('pdf_type'):outcome+='; '+result['metadata']['pdf_type']
            if case.get('table_rows'):outcome+=f"; {len(result['blocks'][0]['rows'])} dòng"
            lines.append(f"| {case['file']} | {recall} | {precision} | {table_score} | {outcome} |")
        except ParseError as error:
            expected=error.code==case.get('error')
            if not expected:failures.append(case['file'])
            lines.append(f"| {case['file']} | Không đo | Không đo | Không đo | {'Đúng lỗi kỳ vọng' if expected else 'Lỗi khác kỳ vọng'}: {error.code} |")
    lines += ['', '## Giới hạn và cách xử lý', '',
              '- Chưa tích hợp OCR tự động. PDF scan/mờ/lệch được giữ file gốc, báo phần thiếu và cần nhập bản đã kiểm tra; không tạo chữ hay điểm tin cậy giả. PDF không có chữ có thể là trang trắng hoặc scan, không khẳng định chắc chắn là scan.',
              '- PDF: bảng có đường kẻ được kiểm tra; bảng không đường kẻ, ô gộp, chữ xoay, font lỗi và bố cục hơn hai cột có thể không phục hồi đúng. Tách hai cột là heuristic, luôn có cảnh báo kiểm tra thứ tự.',
              '- DOCX: giữ thứ tự đoạn/bảng cấp ngoài cùng, đọc header/footer. Bảng lồng, ô gộp, ảnh, textbox và footnote có giới hạn; không phục dựng bố cục trang hay theo dõi sửa đổi.',
              '- XLSX: không chạy công thức/macro/liên kết ngoài. Công thức dùng cache sẵn có; thiếu cache thì đánh dấu ô thiếu, không thay bằng 0. Cache có thể cũ. Ô gộp chỉ lưu ô đầu; sheet ẩn được nêu rõ. Không phục dựng biểu đồ hay định dạng số tiền theo từng ô.',
              '- Giới hạn: 10 MB/file, PDF 200 trang, XLSX 50 sheet, 10.000 dòng/200 cột mỗi sheet; tổng 50.000 ô và 200.000 ký tự. Không cắt im lặng khi vượt giới hạn. Subprocess đọc file có timeout 45 giây; không có giới hạn RAM cứng trên Windows.',
              '- Nội dung đưa vào kho tri thức tối đa 60.000 byte UTF-8 theo cột TEXT hiện có. Tài liệu lớn phải chia nhỏ/hiệu đính; không tự ghi các dòng trích xuất vào sản phẩm, khách hàng hoặc đơn hàng.',
              '- File đúng đuôi vẫn phải qua kiểm tra chữ ký và cấu trúc Office; chặn macro, ZIP giải nén quá lớn, nén bất thường, file rỗng và định dạng cũ. File PDF mã hóa/hỏng bị lỗi, không ghi vào kho tri thức.',
              '- Bản nháp/metadata khác với dữ liệu đã công bố. Title, category, branch scope, content, xác nhận đối chiếu và phiên bản hiện hành phải hợp lệ; thiếu thì không ghi kb_documents. Mọi bản trích xuất phải được người dùng duyệt trước xuất bản.',
              '', '## Tái tạo', '',
              '`python -m pip install -r requirements-dev.txt`, `python scripts/generate_document_samples.py`, '
              '`python -m pytest -q tests/test_document_parser.py tests/test_document_uploads.py`, '
              '`python scripts/report_document_accuracy.py`.', '',
              'API thư viện được đối chiếu với [pdfplumber](https://github.com/jsvine/pdfplumber), '
              '[python-docx](https://python-docx.readthedocs.io/en/latest/_modules/docx/document.html) '
              'và [openpyxl](https://openpyxl.readthedocs.io/en/stable/optimized.html).','']
    target=root/'docs/document_extraction_report.md';target.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Đã đo {len(cases)} mẫu; lỗi khác kỳ vọng: {len(failures)}; báo cáo: {target}')
    return bool(failures)


if __name__=='__main__':raise SystemExit(report())
