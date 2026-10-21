# Các tiện ích hỗ trợ chuẩn bị dữ liệu, cấu hình và kiểm tra triển khai.
"""Tạo bộ tài liệu mô phỏng và đáp án độc lập để đo chất lượng parser."""
from pathlib import Path  # Tạo thư mục và đường dẫn các tài liệu mẫu.
import json  # Ghi manifest đáp án độc lập cho test parser.
from io import BytesIO  # Giữ file PDF trong bộ nhớ khi tạo fixture.
from datetime import date  # Tạo giá trị ngày mẫu cho workbook Excel.

from docx import Document  # Tạo tài liệu Word có đoạn văn, bảng và ô gộp.
from openpyxl import Workbook  # Tạo workbook Excel với bảng, ngày và công thức.
from PIL import Image, ImageDraw, ImageFont, ImageFilter  # Tạo ảnh scan nghiêng/mờ để kiểm thử giới hạn OCR.
from reportlab.pdfgen import canvas  # Tạo PDF nhiều trang, bảng và ảnh.
from reportlab.pdfbase import pdfmetrics  # Đăng ký font để PDF hiển thị tiếng Việt.
from reportlab.pdfbase.ttfonts import TTFont  # Nạp font TTF cho nội dung PDF mẫu.
from reportlab.platypus import Table, TableStyle  # Dựng bảng có đường kẻ trong PDF.
from reportlab.lib import colors  # Chọn màu cho bảng fixture.
from reportlab.lib.utils import ImageReader  # Nhúng ảnh scan vào PDF.
from reportlab.lib.pdfencrypt import StandardEncryption  # Tạo PDF mã hóa dùng cho ca lỗi.


ROOT = Path(__file__).resolve().parents[1] / 'data/samples/documents'


# Sinh fixture PDF/DOCX/XLSX cùng manifest nội dung kỳ vọng cho test parser.
def generate():
    ROOT.mkdir(parents=True, exist_ok=True)
    fonts = [Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font = next((path for path in fonts if path.exists()), None)
    if not font:
        raise RuntimeError('Cần Arial hoặc DejaVu Sans để tạo mẫu có tiếng Việt.')
    pdfmetrics.registerFont(TTFont('SampleVN', str(font)))
    manifest = []

    # Dựng một PDF với font tiếng Việt và các dòng văn bản được cung cấp.
    def pdf(name, lines=None, encrypt=None):
        c = canvas.Canvas(str(ROOT / name), pagesize=(595, 842), encrypt=encrypt)
        c.setFont('SampleVN', 12)
        for index, line in enumerate(lines or []):
            c.drawString(45, 790 - index * 22, line)
        return c

    text = ['Dữ liệu mô phỏng', 'Quy trình kiểm tra tài liệu.', 'Chỉ lưu nội dung đã đối chiếu.']
    c = pdf('text.pdf', text); c.save()
    manifest.append({'file': 'text.pdf', 'text': '\n'.join(text), 'tables': []})
    rows = [['Mã', 'Tên', 'Số lượng'], ['SP01', 'Xe mẫu', '3'], ['SP02', 'Phụ kiện', '7']]
    c = pdf('table.pdf', ['Bảng dữ liệu mô phỏng'])
    table = Table(rows, colWidths=[90, 160, 90], rowHeights=28)
    table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'SampleVN'),('FONTSIZE',(0,0),(-1,-1),11),('GRID',(0,0),(-1,-1),1,colors.black)]))
    table.wrapOn(c, 340, 100); table.drawOn(c, 45, 650); c.save()
    manifest.append({'file':'table.pdf','text':'Bảng dữ liệu mô phỏng','tables':[rows]})
    left = ['CỘT TRÁI', 'Bước một kiểm tra file.', 'Bước hai xác nhận nội dung.']
    right = ['CỘT PHẢI', 'Ghi chú kiểm tra bảng.', 'Không tự đoán dữ liệu thiếu.']
    c = pdf('columns.pdf')
    for index, line in enumerate(left):c.drawString(30,790-index*24,line)
    for index, line in enumerate(right):c.drawString(330,790-index*24,line)
    c.save();manifest.append({'file':'columns.pdf','text':'\n'.join(left+right),'tables':[], 'needs_review':True})
    image = Image.new('RGB',(900,600),'white');draw=ImageDraw.Draw(image)
    draw.text((50,100),'Dữ liệu scan mờ cần được đối chiếu.',font=ImageFont.truetype(str(font),26),fill='black')
    image = image.rotate(4,expand=False,fillcolor='white').filter(ImageFilter.GaussianBlur(1.5))
    c=pdf('scan.pdf');c.drawImage(ImageReader(image),40,400,width=500,height=330);c.save()
    manifest.append({'file':'scan.pdf','pdf_type':'scan_or_empty','needs_review':True})
    c=pdf('mixed.pdf',text);c.showPage();c.drawImage(ImageReader(image),40,400,width=500,height=330);c.save()
    manifest.append({'file':'mixed.pdf','text':'\n'.join(text),'tables':[], 'pdf_type':'mixed','needs_review':True})
    c=pdf('encrypted.pdf',text,StandardEncryption('not-a-secret-sample',canPrint=0));c.save()
    manifest.append({'file':'encrypted.pdf','error':'unreadable_file'})
    c=pdf('large.pdf')
    large=[]
    for page in range(1,81):
        c.setFont('SampleVN',12);line=f'Trang {page}: dữ liệu mô phỏng kiểm thử tài liệu lớn.';large.append(line)
        c.drawString(45,790,line);c.showPage()
    c.save();manifest.append({'file':'large.pdf','text':'\n'.join(large),'tables':[]})
    c=pdf('too_many_pages.pdf')
    for _ in range(201):c.drawString(45,790,'Trang mẫu vượt giới hạn.');c.showPage()
    c.save();manifest.append({'file':'too_many_pages.pdf','error':'page_limit'})
    doc=Document();doc.add_paragraph(text[0]);doc.add_paragraph(text[1])
    table=doc.add_table(rows=0,cols=3)
    for row in rows:
        cells=table.add_row().cells
        for cell,value in zip(cells,row):cell.text=value
    doc.add_paragraph(text[2]);doc.save(ROOT/'table.docx')
    manifest.append({'file':'table.docx','text':'\n'.join(text),'tables':[rows]})
    doc=Document();doc.add_paragraph('Bảng có ô gộp cần được kiểm tra.')
    table=doc.add_table(rows=2,cols=2);table.cell(0,0).merge(table.cell(0,1)).text='Ô gộp';table.cell(1,0).text='A';table.cell(1,1).text='B'
    doc.save(ROOT/'merged.docx');manifest.append({'file':'merged.docx','needs_review':True})
    book=Workbook();sheet=book.active;sheet.title='Dữ liệu'
    for row in rows:sheet.append(row)
    sheet2=book.create_sheet('Ngày');sheet2.append(['Ngày','Số tiền']);sheet2.append([date(2026,10,14),42500000])
    book.save(ROOT/'table.xlsx')
    manifest.append({'file':'table.xlsx','text':'','tables':[rows,[['Ngày','Số tiền'],['14/10/2026 00:00:00','42500000']]],'needs_review':True})
    book=Workbook();sheet=book.active;sheet.title='Công thức';sheet.append(['Số lượng','Đơn giá','Tổng']);sheet.append([3,100,'=A2*B2']);book.save(ROOT/'formula.xlsx')
    manifest.append({'file':'formula.xlsx','needs_review':True})
    book=Workbook();sheet=book.active;sheet.title='Lớn';sheet.append(['Mã','Tên','Số lượng'])
    for n in range(1,2001):sheet.append([f'SP{n:04}','Dữ liệu mô phỏng',n])
    book.save(ROOT/'large.xlsx');manifest.append({'file':'large.xlsx','table_rows':2001,'needs_review':True})
    book=Workbook();sheet=book.active;sheet.cell(10001,1,'Vượt giới hạn');book.save(ROOT/'too_many_rows.xlsx')
    manifest.append({'file':'too_many_rows.xlsx','error':'cell_limit'})
    (ROOT/'corrupt.pdf').write_bytes(b'%PDF-1.7\nFile bi hong')
    manifest.append({'file':'corrupt.pdf','error':'unreadable_file'})
    (ROOT/'wrong_extension.pdf').write_bytes(b'Khong phai PDF')
    manifest.append({'file':'wrong_extension.pdf','error':'format_mismatch'})
    (ROOT/'corrupt.docx').write_bytes(b'PK\x03\x04broken')
    manifest.append({'file':'corrupt.docx','error':'corrupt_file'})
    (ROOT/'empty.xlsx').write_bytes(b'')
    manifest.append({'file':'empty.xlsx','error':'file_size'})
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Đã tạo {len(manifest)} mẫu tại {ROOT}')


if __name__=='__main__':generate()
