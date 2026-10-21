import json  # Đọc hoặc ghi dữ liệu JSON trong luồng xử lý của file.
import re  # Tìm và chuẩn hóa mẫu văn bản bằng biểu thức chính quy.
from collections import Counter  # Đếm phần tử để so sánh dữ liệu.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
from zipfile import ZipFile, ZIP_DEFLATED  # Tạo hoặc kiểm tra cấu trúc archive Office.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from document_parser import parse_document, ParseError, validate_file  # Dùng parser và giới hạn xử lý file.

SAMPLES = Path(__file__).resolve().parents[1] / 'data/samples/documents'
CASES = json.loads((SAMPLES / 'manifest.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['file'])
def test_sample_against_independent_gold(case):
    if 'error' in case:
        with pytest.raises(ParseError) as error:
            parse_document(SAMPLES / case['file'])
        assert error.value.code == case['error']
        return
    result = parse_document(SAMPLES / case['file'])
    assert result['schema_version'] == 1 and result['quality']['confidence'] is None
    assert result['quality']['ocr_used'] is False
    if 'text' in case:
        actual = '\n'.join(b['text'] for b in result['blocks'] if b['kind'] == 'text')
        assert Counter(re.findall(r'\S+',actual)) == Counter(re.findall(r'\S+',case['text']))
    if 'tables' in case:
        assert [b['rows'] for b in result['blocks'] if b['kind'] == 'table'] == case['tables']
    if 'needs_review' in case:
        assert result['quality']['state'] == 'needs_review'
    if 'pdf_type' in case:
        assert result['metadata']['pdf_type'] == case['pdf_type']
    if 'table_rows' in case:
        assert len(result['blocks'][0]['rows']) == case['table_rows']


def test_pdf_columns_keep_separate_reading_order():
    result = parse_document(SAMPLES / 'columns.pdf')
    assert [b['location']['column'] for b in result['blocks']] == [1,2]
    assert result['blocks'][0]['text'].startswith('CỘT TRÁI')
    assert result['blocks'][1]['text'].startswith('CỘT PHẢI')


def test_docx_keeps_paragraph_table_paragraph_order():
    result = parse_document(SAMPLES / 'table.docx')
    assert [b['kind'] for b in result['blocks']] == ['text','text','table','text']
    assert result['blocks'][-1]['text'] == 'Chỉ lưu nội dung đã đối chiếu.'


def test_formulas_without_cache_are_not_assumed_zero():
    result = parse_document(SAMPLES / 'formula.xlsx')
    assert result['metadata']['missing_formula_cells'] == ['Công thức!C2']
    assert result['blocks'][0]['rows'][1][-1] == '[Chưa có kết quả công thức]'
    assert result['quality']['state'] == 'needs_review'


def test_scan_coverage_is_not_ocr_accuracy():
    result = parse_document(SAMPLES / 'scan.pdf')
    assert result['text'] == '' and result['metadata']['text_page_coverage'] == 0
    assert result['metadata']['missing_text_pages'] == [1]


def test_reject_archive_bomb_and_macros(tmp_path):
    bomb=tmp_path/'bomb.docx'
    with ZipFile(bomb,'w',compression=ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','x');z.writestr('word/document.xml',b'x'*(2*1024*1024))
    with pytest.raises(ParseError) as error:validate_file(bomb,'docx')
    assert error.value.code == 'archive_limit'
    macro=tmp_path/'macro.docx'
    with ZipFile(macro,'w') as z:
        z.writestr('[Content_Types].xml','x');z.writestr('word/document.xml','x');z.writestr('word/vbaProject.bin','x')
    with pytest.raises(ParseError) as error:validate_file(macro,'docx')
    assert error.value.code == 'macros_not_supported'
    entity=tmp_path/'entity.docx'
    with ZipFile(entity,'w') as z:
        z.writestr('[Content_Types].xml','x');z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY y SYSTEM "file:///secret">]><x>&y;</x>')
    with pytest.raises(ParseError) as error:validate_file(entity,'docx')
    assert error.value.code == 'unsafe_xml'
