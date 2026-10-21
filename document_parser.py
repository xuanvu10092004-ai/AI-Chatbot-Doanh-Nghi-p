# File này đọc PDF, DOCX, XLSX và chuyển nội dung thành dữ liệu có thể tìm kiếm.
from __future__ import annotations

import json  # Xuất kết quả parser dạng JSON cho tiến trình gọi.
import re  # Loại ký tự điều khiển trong văn bản được trích xuất.
import sys  # Đọc đối số file và ghi kết quả từ CLI subprocess.
import unicodedata  # Chuẩn hóa chữ tiếng Việt về Unicode NFC.
from datetime import date, datetime  # Định dạng ngày và thời gian lấy từ Excel.
from pathlib import Path  # Kiểm tra file và chuẩn hóa đường dẫn tài liệu.
from zipfile import ZipFile, BadZipFile  # Kiểm tra cấu trúc DOCX/XLSX và giới hạn archive.

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_CELLS = 50000
MAX_CHARS = 200000
PARSER_VERSION = '1.0'


# Lỗi parse có mã ổn định để service lưu trạng thái lỗi cho file.
class ParseError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


# Chuẩn hóa ngày, Unicode và ký tự điều khiển trước khi lưu nội dung trích xuất.
def clean(value) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y %H:%M:%S')
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    text = unicodedata.normalize('NFC', str(value)).replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return '\n'.join(line.rstrip() for line in text.split('\n')).strip()


# Kiểm tra đuôi, chữ ký file và cấu trúc archive trước khi bộ đọc mở tài liệu.
def validate_file(path: Path, file_format: str):
    if file_format not in {'pdf', 'docx', 'xlsx'}:
        raise ParseError('unsupported_format', 'Chỉ hỗ trợ PDF, DOCX và XLSX; không nhận DOC/XLS cũ hoặc file có macro.')
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ParseError('file_size', 'File phải có dữ liệu và không vượt quá 10 MB.')
    with path.open('rb') as stream:
        magic = stream.read(8)
    if file_format == 'pdf':
        if not magic.startswith(b'%PDF-'):
            raise ParseError('format_mismatch', 'Nội dung file không phải PDF dù có đuôi PDF.')
        return
    if not magic.startswith(b'PK'):
        raise ParseError('format_mismatch', 'Nội dung file không khớp định dạng Word/Excel đã chọn.')
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > 60 * 1024 * 1024:
                raise ParseError('archive_limit', 'File giải nén quá lớn hoặc có quá nhiều thành phần.')
            if any(e.flag_bits & 1 or (e.file_size > 1024 * 1024 and e.file_size / max(1, e.compress_size) > 200) for e in entries):
                raise ParseError('archive_limit', 'File mã hóa hoặc có mức nén vượt giới hạn an toàn.')
            names = set(archive.namelist())
            required = 'word/document.xml' if file_format == 'docx' else 'xl/workbook.xml'
            if '[Content_Types].xml' not in names or required not in names:
                raise ParseError('format_mismatch', 'Cấu trúc bên trong không khớp định dạng file.')
            if any('vbaproject' in name.casefold() for name in names):
                raise ParseError('macros_not_supported', 'Không tiếp nhận tài liệu chứa macro.')
            for entry in entries:
                if entry.filename.endswith('.xml'):
                    xml = archive.read(entry)
                    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                        raise ParseError('unsafe_xml', 'Không tiếp nhận file Office có khai báo thực thể XML.')
    except BadZipFile:
        raise ParseError('corrupt_file', 'File Word/Excel bị hỏng hoặc không đọc được cấu trúc.') from None


def _text_from_words(words):
    lines = []
    for word in sorted(words, key=lambda w: (round(w['top'] / 3), w['x0'])):
        if not lines or abs(lines[-1][0] - word['top']) > 3:
            lines.append((word['top'], [word['text']]))
        else:
            lines[-1][1].append(word['text'])
    return '\n'.join(' '.join(parts) for _, parts in lines)


def _pdf(path, add_text, add_table, warnings):
    # Trích văn bản/bảng theo trang; ghi cảnh báo khi trang scan hoặc có ảnh.
    import pdfplumber  # Đọc nội dung PDF để xác nhận chứng từ.
    missing = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        if total > MAX_PAGES:
            raise ParseError('page_limit', 'PDF vượt giới hạn 200 trang. Hãy chia thành các tài liệu nhỏ hơn.')
        for number, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            if not words:
                missing.append(number)
                continue
            tables = page.find_tables()
            for index, table in enumerate(tables, 1):
                add_table(table.extract(), {'page': number, 'table': index})
            # Không nhân đôi chữ trong bảng vào phần văn bản.
            words = [w for w in words if not any(b.bbox[0] <= w['x0'] and w['x1'] <= b.bbox[2]
                                                 and b.bbox[1] <= w['top'] and w['bottom'] <= b.bbox[3] for b in tables)]
            mid = page.width / 2
            left = [w for w in words if w['x1'] < mid - 10]
            right = [w for w in words if w['x0'] > mid + 10]
            crossing = [w for w in words if w not in left and w not in right]
            if len(left) >= 4 and len(right) >= 4 and len(crossing) <= 2:
                if crossing:
                    add_text(_text_from_words(crossing), {'page': number, 'section': 'heading'})
                add_text(_text_from_words(left), {'page': number, 'column': 1})
                add_text(_text_from_words(right), {'page': number, 'column': 2})
                warnings.append(f'Trang {number}: nhận diện hai cột theo vị trí; cần kiểm tra thứ tự đọc.')
            else:
                add_text(_text_from_words(words), {'page': number})
            if page.images:
                warnings.append(f'Trang {number}: có ảnh; chữ nằm trong ảnh chưa được trích xuất.')
            page.close()
    if missing:
        warnings.append('Trang không có lớp văn bản hoặc trống: ' + ', '.join(map(str, missing)) + '. Cần OCR hoặc nhập và kiểm tra thủ công.')
    return {'pages': total, 'missing_text_pages': missing,
            'pdf_type': 'scan_or_empty' if len(missing) == total else 'mixed' if missing else 'text',
            'text_page_coverage': (total - len(missing)) / total if total else 0}


def _docx(path, add_text, add_table, warnings):
    # Đọc đoạn văn, bảng, header/footer và báo các cấu trúc Office chưa hỗ trợ đầy đủ.
    from docx import Document  # Tạo tài liệu Word mẫu có bảng và nội dung.
    from docx.table import Table  # Tạo tài liệu Word mẫu có bảng và nội dung.
    document = Document(path)
    for index, block in enumerate(document.iter_inner_content(), 1):
        if isinstance(block, Table):
            add_table([[cell.text for cell in row.cells] for row in block.rows], {'block': index})
        else:
            add_text(block.text, {'block': index})
    for index, section in enumerate(document.sections, 1):
        for name, part in [('header', section.header), ('footer', section.footer)]:
            for paragraph in part.paragraphs:
                add_text(paragraph.text, {'section': index, 'part': name})
    if document.inline_shapes:
        warnings.append('Word có ảnh; chữ trong ảnh chưa được đọc. Hộp văn bản, SmartArt và bảng lồng cần kiểm tra thủ công.')
    with ZipFile(path) as archive:
        if any(b'tbl' in el.tag.encode() for el in document.element.body.iter() if el.getparent() is not None and el.getparent().tag.endswith('}tc')):
            warnings.append('Word có bảng lồng; cần kiểm tra nội dung và ô gộp.')
        xml = archive.read('word/document.xml')
        if b'txbxContent' in xml:
            warnings.append('Word có hộp văn bản chưa được trích xuất đầy đủ.')
        if b'gridSpan' in xml or b'vMerge' in xml:
            warnings.append('Word có ô gộp; cần kiểm tra ô lặp và các giá trị còn thiếu.')
        if b'w:drawing' in xml or b'w:pict' in xml:
            warnings.append('Word có đối tượng hình ảnh; chữ trong ảnh chưa được OCR.')
        if 'word/footnotes.xml' in archive.namelist() or 'word/endnotes.xml' in archive.namelist():
            warnings.append('Word có chú thích cuối trang/cuối tài liệu chưa được trích xuất.')
    return {'blocks': len(list(document.iter_inner_content()))}


def _xlsx(path, add_text, add_table, warnings):
    # Đọc giá trị công thức đã lưu, ghi cảnh báo với ô chưa tính và sheet ẩn.
    from openpyxl import load_workbook  # Đọc hoặc tạo workbook Excel.
    book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    missing_formulas, hidden = [], []
    try:
        if len(book.worksheets) > 50:
            raise ParseError('sheet_limit', 'Excel vượt giới hạn 50 sheet.')
        for sheet in book:
            if sheet.max_row > 10000 or sheet.max_column > 200 or sheet.max_row * sheet.max_column > MAX_CELLS:
                raise ParseError('cell_limit', 'Sheet vượt giới hạn 10.000 dòng, 200 cột hoặc 50.000 ô.')
            if sheet.sheet_state != 'visible':
                hidden.append(sheet.title)
            values = cached[sheet.title].iter_rows()
            rows = []
            for row in sheet.iter_rows():
                cached_row = next(values, ())
                output = []
                for index, cell in enumerate(row):
                    if cell.data_type == 'f':
                        value = cached_row[index].value if index < len(cached_row) else None
                        if value is None:
                            missing_formulas.append(f'{sheet.title}!{cell.coordinate}')
                            output.append('[Chưa có kết quả công thức]')
                        else:
                            output.append(value)
                    elif cell.data_type == 'e':
                        output.append('[Ô có lỗi]')
                        warnings.append(f'{sheet.title}!{cell.coordinate}: ô Excel có lỗi.')
                    else:
                        output.append(cell.value)
                rows.append(output)
            while rows and not any(v is not None and v != '' for v in rows[-1]):
                rows.pop()
            if rows:
                add_table(rows, {'sheet': sheet.title, 'start_row': 1})
        if missing_formulas:
            warnings.append('Công thức chưa có giá trị lưu sẵn: ' + ', '.join(missing_formulas[:30]) + '. Không tự tính hoặc coi là số 0.')
        if hidden:
            warnings.append('Có sheet ẩn được trích xuất: ' + ', '.join(hidden))
        with ZipFile(path) as archive:
            if any(name.startswith('xl/media/') for name in archive.namelist()):
                warnings.append('Excel có ảnh; chữ trong ảnh chưa được OCR.')
        warnings.append('Excel: ô gộp giữ giá trị tại ô đầu; số liệu/định dạng và giá trị công thức lưu sẵn cần được người dùng kiểm tra.')
        return {'sheets': len(book.worksheets), 'missing_formula_cells': missing_formulas}
    finally:
        book.close()
        cached.close()


# Chuẩn hóa đầu vào trong bước parse_document để các phép so khớp phía sau dùng cùng một dạng.
def parse_document(path: str | Path, file_format: str | None = None):
    # Giới hạn kích thước văn bản/bảng và đóng gói nội dung cùng cảnh báo chất lượng.
    path = Path(path)
    file_format = file_format or path.suffix.lower().lstrip('.')
    validate_file(path, file_format)
    blocks, warnings, chars, cells = [], [], 0, 0

    def add_text(text, location):
        nonlocal chars
        text = clean(text)
        chars += len(text)
        if chars > MAX_CHARS:
            raise ParseError('text_limit', 'Nội dung vượt giới hạn 200.000 ký tự; hãy chia nhỏ tài liệu.')
        if text:
            blocks.append({'kind': 'text', 'location': location, 'text': text})

    def add_table(rows, location):
        nonlocal chars, cells
        rows = [[clean(value) for value in row] for row in rows]
        cells += sum(len(row) for row in rows)
        chars += sum(len(value) for row in rows for value in row)
        if cells > MAX_CELLS or chars > MAX_CHARS:
            raise ParseError('content_limit', 'Nội dung bảng vượt giới hạn 50.000 ô hoặc 200.000 ký tự.')
        if rows and any(any(row) for row in rows):
            blocks.append({'kind': 'table', 'location': location, 'rows': rows})

    try:
        metadata = {'pdf': _pdf, 'docx': _docx, 'xlsx': _xlsx}[file_format](path, add_text, add_table, warnings)
    except ParseError:
        raise
    except Exception:
        raise ParseError('unreadable_file', 'Không đọc được file. File có thể bị hỏng, mã hóa hoặc có cấu trúc không được hỗ trợ.') from None
    text = '\n\n'.join(b['text'] if b['kind'] == 'text' else '\n'.join('\t'.join(row) for row in b['rows']) for b in blocks)
    if not text.strip():
        warnings.append('Chưa có nội dung sử dụng được. Cần bổ sung văn bản đã kiểm tra trước khi lưu vào kho tri thức.')
    return {'schema_version': 1, 'parser_version': PARSER_VERSION, 'format': file_format,
            'blocks': blocks, 'text': text, 'metadata': metadata,
            'quality': {'state': 'needs_review' if warnings or not text else 'extracted',
                        'warnings': list(dict.fromkeys(warnings)), 'ocr_used': False,
                        'confidence': None, 'confidence_note': 'Không có điểm tin cậy OCR; bản trích xuất cần được đối chiếu với file gốc.'},
            'counts': {'text_characters': len(text), 'table_cells': cells, 'tables': sum(b['kind'] == 'table' for b in blocks)}}


if __name__ == '__main__':
    try:
        result = {'ok': True, 'result': parse_document(sys.argv[1], sys.argv[2])}
    except ParseError as error:
        result = {'ok': False, 'code': error.code, 'message': str(error)}
    except Exception:
        result = {'ok': False, 'code': 'parser_failed', 'message': 'Bộ đọc file không hoàn tất; hãy kiểm tra lại file hoặc thử lại.'}
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
