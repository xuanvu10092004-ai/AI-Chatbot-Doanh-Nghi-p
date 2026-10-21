# Trả dữ liệu từng widget dashboard sau khi áp dụng phạm vi quyền của user.
from flask import g  # Cung cấp user hiện tại cho bộ lọc bản ghi sở hữu.
from db import cursor  # Chạy các phép tổng hợp trên đơn, khách, tồn và sản phẩm.
from security import permissions  # Lấy scope all, branch hoặc own cho từng permission.

WIDGETS={
 'orders':('Đơn hàng & doanh thu',('order:read',)),
 'inventory':('Tồn kho',('inventory:read',)),
 'customers':('Khách hàng',('customer:read',)),
 'revenue-month':('Doanh thu theo tháng',('order:read',)),
 'revenue-branch':('Doanh thu theo chi nhánh',('order:read',)),
 'inventory-branch':('Tồn kho theo chi nhánh',('inventory:read',)),
 'customer-status':('Khách theo trạng thái',('customer:read',)),
 'customer-source':('Khách theo nguồn',('customer:read',)),
 'bestsellers':('Mẫu xe bán chạy',('order:read',)),
 'profit':('Lợi nhuận gộp theo mẫu xe',('dashboard:finance','price:cost:read')),
}


def scope_filter(code,alias,owner=None):
    # Chuyển scope quyền thành điều kiện SQL và tuple tham số, không nhận tên cột từ request.
    grant=permissions()[code]
    if grant['scope']=='all':return '1=1',()
    if grant['scope']=='branch':return alias+' = %s',(grant['branch'],)
    if owner and g.user:return owner+' = %s',(g.user['id'],)
    return '1=0',()


def widget_data(widget):
    # Chọn truy vấn tổng hợp tương ứng với widget đã được whitelist ở WIDGETS.
    if widget in {'inventory','inventory-branch'}:
        where,params=scope_filter('inventory:read','i.branch_id')
        select='COALESCE(SUM(i.quantity),0) AS total_stock,COALESCE(SUM(i.quantity=0),0) AS empty_rows' if widget=='inventory' else 'b.code AS label,SUM(i.quantity) AS value'
        query=f'SELECT {select} FROM inventory i JOIN branches b ON b.id=i.branch_id WHERE {where}'
        if widget=='inventory-branch':query+=' GROUP BY b.id,b.code ORDER BY b.code'
    elif widget.startswith('customer'):
        where,params=scope_filter('customer:read','u.home_branch_id','u.id')
        column={'customer-status':'cp.status','customer-source':'cp.lead_source'}.get(widget)
        select='COUNT(*) AS customers' if not column else column+' AS label,COUNT(*) AS value'
        query=f'SELECT {select} FROM users u JOIN customer_profiles cp ON cp.user_id=u.id WHERE {where}'
        if column:query+=f' GROUP BY {column} ORDER BY value DESC,label'
    elif widget=='profit':
        filters=[];params=()
        for code in ('dashboard:finance','price:cost:read'):
            where,values=scope_filter(code,'o.branch_id','o.customer_id');filters.append(where);params+=values
        query='SELECT p.model_name AS label,SUM((oi.unit_price-pv.cost_price)*oi.quantity)-SUM(o.discount_amount*oi.quantity*oi.unit_price/NULLIF(t.gross,0)) AS value FROM orders o JOIN order_items oi ON oi.order_id=o.id JOIN product_variants pv ON pv.id=oi.variant_id JOIN products p ON p.id=pv.product_id JOIN (SELECT order_id,SUM(quantity*unit_price) AS gross FROM order_items GROUP BY order_id) t ON t.order_id=o.id WHERE '+' AND '.join(filters)+' GROUP BY p.id,p.model_name ORDER BY value DESC,label'
    else:
        where,params=scope_filter('order:read','o.branch_id','o.customer_id')
        if widget=='bestsellers':
            query=f'SELECT p.model_name AS label,SUM(oi.quantity) AS value FROM orders o JOIN order_items oi ON oi.order_id=o.id JOIN product_variants pv ON pv.id=oi.variant_id JOIN products p ON p.id=pv.product_id WHERE {where} GROUP BY p.id,p.model_name ORDER BY value DESC,label LIMIT 5'
        else:
            source='orders o JOIN (SELECT order_id,SUM(quantity*unit_price) AS gross FROM order_items GROUP BY order_id) t ON t.order_id=o.id JOIN branches b ON b.id=o.branch_id'
            group="DATE_FORMAT(o.created_at,'%Y-%m')" if widget=='revenue-month' else 'b.code' if widget=='revenue-branch' else None
            # % được escape cho mysql-connector khi có bind parameters.
            select='COALESCE(SUM(t.gross-o.discount_amount),0) AS net_revenue,COUNT(*) AS orders' if not group else group+' AS label,SUM(t.gross-o.discount_amount) AS value'
            query=f'SELECT {select} FROM {source} WHERE {where}'
            if group:query+=f' GROUP BY {group} ORDER BY label'
    with cursor() as cur:
        cur.execute(query,params);return cur.fetchall()
