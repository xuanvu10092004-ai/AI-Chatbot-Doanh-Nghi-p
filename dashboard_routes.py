# Đăng ký trang tổng quan và endpoint riêng cho từng widget.
from flask import render_template, jsonify  # Trả trang dashboard và dữ liệu widget dạng JSON.
from security import require_permission, permissions  # Lọc quyền ở backend trước khi dựng hoặc tải widget.
from dashboard_service import WIDGETS, widget_data  # Lấy danh sách widget và truy vấn số liệu tương ứng.


# Đăng ký các endpoint của nhóm dashboard để Flask chuyển request vào đúng hàm.
def register_dashboard(app):
    @app.get('/dashboard')
    @require_permission('dashboard:view')
    def dashboard_page():
        # Chỉ đưa widget có đủ permission vào template.
        visible=[{'code':code,'title':title} for code,(title,codes) in WIDGETS.items() if all(c in permissions() for c in codes)]
        return render_template('dashboard.html',widgets=visible)
    for code,(_,codes) in WIDGETS.items():
        # Mặc định hóa code ở closure để mỗi URL gọi đúng widget đã đăng ký.
        def handler(widget=code):return jsonify(rows=widget_data(widget))
        app.add_url_rule('/api/dashboard/'+code,endpoint='widget_'+code,view_func=require_permission(*codes)(handler))
