"""Đăng ký trang/API bán hàng và tạo chứng từ PDF mô phỏng từ đơn hàng."""

from io import BytesIO  # Giữ PDF đã tạo trong bộ nhớ trước khi gửi response.
from pathlib import Path  # Tìm font chữ tiếng Việt trong thư mục static.
from threading import Lock  # Ngăn đăng ký font PDF đồng thời nhiều lần.
from xml.sax.saxutils import escape  # Escape dữ liệu khách/đơn trước khi đưa vào Paragraph PDF.

from flask import g, jsonify, render_template, request, send_file  # Nhận filter, dựng trang và gửi chứng từ.
from reportlab.lib import colors  # Tô nền và viền bảng trong chứng từ.
from reportlab.lib.styles import ParagraphStyle  # Thiết lập font và cỡ chữ PDF.
from reportlab.lib.pagesizes import A4  # Chọn khổ A4 cho chứng từ mô phỏng.
from reportlab.pdfbase import pdfmetrics  # Đăng ký font để render tiếng Việt.
from reportlab.pdfbase.ttfonts import TTFont  # Nạp font TTF cục bộ cho PDF.
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # Dựng chữ, khoảng cách và bảng dòng hàng.

from db import cursor  # Đọc đơn hàng, khách hàng và dòng sản phẩm trong MySQL.
from dashboard_service import scope_filter  # Giới hạn danh sách/chứng từ theo quyền và phạm vi.
from security import require_permission, audit  # Kiểm tra quyền xuất và ghi audit xuất chứng từ.

STATUS_LABELS = {'pending':'Chờ duyệt','approved':'Đã duyệt','paid':'Đã thanh toán',
                 'delivered':'Đã giao xe','cancelled':'Đã hủy'}
FONT_LOCK = Lock()


def money(value):
    return f'{int(value):,}'.replace(',', '.') + ' ₫'


def invoice_pdf(order, items):
    # Tính tổng/giảm giá, tạo chứng từ mô phỏng và không khẳng định đơn chưa thanh toán.
    with FONT_LOCK:
        if 'InvoiceNoto' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('InvoiceNoto', str(Path(__file__).parent/'static/vendor/fonts/NotoSans-Regular.ttf')))
    style=ParagraphStyle('Invoice',fontName='InvoiceNoto',fontSize=10,leading=16)
    heading=ParagraphStyle('Heading',parent=style,fontSize=16,leading=23)
    p=lambda value:Paragraph(escape(str(value)),style)
    gross=sum(int(item['quantity'])*int(item['unit_price']) for item in items)
    discount=int(order['discount_amount'])
    if not items or any(int(i['quantity'])<=0 or int(i['unit_price'])<=0 for i in items) or not 0<=discount<=gross:
        raise ValueError('Đơn thiếu mặt hàng hoặc số tiền không hợp lệ; chưa thể xuất PDF.')
    paid=order['status'] in {'paid','delivered'}
    title='Hóa đơn bán hàng (mô phỏng)' if paid else 'Phiếu xác nhận đơn hàng (mô phỏng)'
    story=[Paragraph(title,heading),p(f"Số chứng từ: MP-{order['id']:06d} · Chi nhánh: {order['branch_code']}"),
           p('Ngày lập đơn: '+order['created_at'].strftime('%d/%m/%Y')),
           p('Trạng thái: '+STATUS_LABELS[order['status']]),Spacer(1,12),
           p('Khách hàng: '+order['full_name']),p('Điện thoại: '+(order['phone'] or 'Chưa cung cấp')),
           p('Email: '+order['email']),
           p('Địa chỉ: '+(', '.join(str(order.get(k) or '') for k in ('address','district','province') if order.get(k)) or 'Chưa cung cấp')),
           Spacer(1,12)]
    rows=[[p(v) for v in ['Xe / Phiên bản','SL','Đơn giá','Thành tiền']]]
    for item in items:
        rows.append([p(item['variant_name']),p(item['quantity']),p(money(item['unit_price'])),p(money(int(item['quantity'])*int(item['unit_price'])))])
    table=Table(rows,colWidths=[225,30,105,115],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf1f7')),
                               ('GRID',(0,0),(-1,-1),0.4,colors.lightgrey),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([table,Spacer(1,12),p('Tổng tiền hàng: '+money(gross)),p('Giảm giá: '+money(discount)),
                  p('Tổng giá trị đơn: '+money(gross-discount)),Spacer(1,16),
                  p('Dữ liệu mô phỏng. Chứng từ hỗ trợ đề tài, không phải hóa đơn điện tử thuế.')])
    if not paid:story.append(p('Đơn chưa xác nhận thanh toán. Phiếu này không xác nhận đã thu tiền hoặc giao xe.'))
    out=BytesIO()
    def footer(canvas,doc):
        canvas.setFont('InvoiceNoto',9);canvas.drawString(45,25,f'Dữ liệu mô phỏng · Trang {doc.page}')
    SimpleDocTemplate(out,pagesize=A4,rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=45,
                      title=title,author='Hệ thống dữ liệu mô phỏng').build(story,onFirstPage=footer,onLaterPages=footer)
    out.seek(0)
    return out


# Đăng ký các endpoint của nhóm sales để Flask chuyển request vào đúng hàm.
def register_sales(app):
    @app.get('/orders')
    @require_permission('order:read')
    def sales_orders_page():return render_template('orders.html',statuses=STATUS_LABELS)

    @app.get('/api/orders')
    @require_permission('order:read')
    def sales_orders_list():
        try:page=max(1,int(request.args.get('page',1)))
        except ValueError:return jsonify(message='Trang không hợp lệ.'),400
        where,params=scope_filter('order:read','o.branch_id','o.customer_id')
        status=request.args.get('status')
        if status:
            if status not in STATUS_LABELS:return jsonify(message='Trạng thái không hợp lệ.'),400
            where+=' AND o.status=%s';params+=(status,)
        query=request.args.get('q','').strip()[:200]
        if query:where+=' AND (u.full_name LIKE %s OR u.email LIKE %s)';params+=('%'+query+'%','%'+query+'%')
        source='orders o JOIN users u ON u.id=o.customer_id JOIN branches b ON b.id=o.branch_id'
        with cursor() as cur:
            cur.execute('SELECT COUNT(*) AS total FROM '+source+' WHERE '+where,params);total=cur.fetchone()['total']
            cur.execute('SELECT o.id,o.status,o.created_at,b.code AS branch_code,u.full_name, '
                        '(SELECT SUM(oi.quantity*oi.unit_price) FROM order_items oi WHERE oi.order_id=o.id)-o.discount_amount AS amount FROM '+source+' WHERE '+where+' ORDER BY o.id DESC LIMIT 20 OFFSET %s',(*params,(page-1)*20))
            rows=cur.fetchall()
        return jsonify(rows=rows,total=total,page=page,size=20)

    @app.get('/api/orders/<int:order_id>/invoice.pdf')
    @require_permission('order:read','invoice:export')
    def sales_invoice_export(order_id):
        filters=[];params=()
        for code in ('order:read','invoice:export'):
            where,values=scope_filter(code,'o.branch_id','o.customer_id');filters.append(where);params+=values
        with cursor() as cur:
            cur.execute('SELECT o.*,b.code AS branch_code,u.full_name,u.phone,u.email,cp.address,cp.district,cp.province FROM orders o JOIN branches b ON b.id=o.branch_id JOIN users u ON u.id=o.customer_id LEFT JOIN customer_profiles cp ON cp.user_id=u.id WHERE o.id=%s AND '+' AND '.join(filters),(order_id,*params))
            order=cur.fetchone()
            if not order:return jsonify(message='Không thể xuất chứng từ cho yêu cầu này.'),404
            if order['status']=='cancelled':return jsonify(message='Đơn đã hủy, không thể xuất chứng từ bán hàng.'),409
            cur.execute('SELECT oi.quantity,oi.unit_price,pv.variant_name FROM order_items oi JOIN product_variants pv ON pv.id=oi.variant_id WHERE oi.order_id=%s ORDER BY oi.variant_id',(order_id,))
            try:output=invoice_pdf(order,cur.fetchall())
            except ValueError as error:return jsonify(message=str(error)),409
            audit(cur,'invoice_export','order',order_id,after={'status':order['status']},actor=g.user['id'])
        return send_file(output,mimetype='application/pdf',as_attachment=True,download_name=f'chung_tu_MP-{order_id:06d}.pdf')
