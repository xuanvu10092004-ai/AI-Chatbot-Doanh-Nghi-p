from datetime import datetime, timedelta  # Tính giới hạn thời gian đặt lịch.
from zoneinfo import ZoneInfo  # Diễn giải giờ hẹn theo múi giờ Việt Nam.
import re  # Chuẩn hóa số điện thoại và kiểm tra email.
from flask import g  # Lấy user đã xác thực trong request hiện tại.
from db import cursor  # Đọc và ghi yêu cầu đặt lịch trong MySQL.
from security import permissions, audit  # Kiểm tra quyền và lưu dấu vết thay đổi lịch.
from operations_routes import number, text, OperationRejected  # Dùng lại kiểm tra đầu vào chung của API.
from dashboard_service import scope_filter  # Giới hạn truy vấn theo chi nhánh hoặc chủ sở hữu.


# Kiểm tra quyền, chi nhánh, giờ hẹn và thông tin liên hệ trước khi tạo lịch.
def create_appointment(data,session_id):
    branch=number(data,'branch_id',1,2**31-1)
    kind=data.get('kind')
    if kind not in {'maintenance','consultation'}:raise OperationRejected('Khách có thể đặt lịch bảo dưỡng hoặc tư vấn.')
    grant=permissions().get('booking:create')
    if g.user and g.user['user_type']=='staff' and grant and grant['scope']=='branch' and branch!=grant['branch']:
        raise OperationRejected('Thông tin đặt lịch ngoài phạm vi được cấp.',403)
    try:scheduled=datetime.fromisoformat(str(data.get('scheduled_at','')))
    except ValueError:raise OperationRejected('Ngày giờ không hợp lệ, dùng dd/MM/yyyy HH:mm hoặc yyyy-mm-ddTHH:mm.') from None
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).replace(tzinfo=None)
    if scheduled.tzinfo or not now+timedelta(minutes=10)<=scheduled<=now+timedelta(days=180) or not 7<=scheduled.hour<18:
        raise OperationRejected('Chọn giờ Việt Nam 07:00–18:00, trước ít nhất 10 phút, trong 180 ngày.')
    customer=g.user['id'] if g.user and g.user['user_type']=='customer' else None
    person={**data}
    if customer:
        person.update(full_name=g.user['full_name'],email=g.user['email'],phone=data.get('phone') or g.user['phone'])
    name=text(person,'full_name',150);phone=re.sub(r'[ .()-]','',text(person,'phone',20))
    if not re.fullmatch(r'(?:0\d{9,10}|\+84\d{9,10})',phone):raise OperationRejected('Số điện thoại không hợp lệ.')
    email=text(person,'email',255,False)
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@.]+',email):raise OperationRejected('Email không hợp lệ.')
    notes=text(person,'notes',1000,False)
    with cursor() as cur:
        cur.execute('SELECT id FROM branches WHERE id=%s FOR UPDATE',(branch,))
        if not cur.fetchone():raise OperationRejected('Chi nhánh không hợp lệ.')
        cur.execute("SELECT id FROM appointment_requests WHERE phone=%s AND scheduled_at=%s AND status IN ('scheduled','confirmed') FOR UPDATE",(phone,scheduled))
        if cur.fetchone():raise OperationRejected('Yêu cầu chưa thể ghi nhận tại thời điểm này. Vui lòng chọn giờ khác.',409)
        cur.execute('''INSERT INTO appointment_requests(session_id,customer_id,branch_id,kind,full_name,phone,email,scheduled_at,notes)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(session_id,customer,branch,kind,name,phone,email or None,scheduled,notes))
        target=cur.lastrowid
        audit(cur,'appointment_create','appointment',target,after={'kind':kind,'branch_id':branch,'scheduled_at':scheduled},actor=g.user['id'] if g.user else None)
    return {'id':target,'status':'scheduled','message':'Đã nhận lịch, chờ nhân viên xác nhận.'}


# Chỉ liệt kê lịch nằm trong phạm vi chi nhánh hoặc user được cấp quyền.
def list_appointments():
    where,params=scope_filter('booking:read','a.branch_id','a.customer_id')
    with cursor() as cur:
        cur.execute('''SELECT a.id,a.customer_id,a.kind,a.full_name,a.phone,a.scheduled_at,a.status,a.version,
                    b.code AS branch_code FROM appointment_requests a JOIN branches b ON b.id=a.branch_id
                    WHERE '''+where+' ORDER BY a.scheduled_at DESC,a.id DESC LIMIT 100',params)
        return cur.fetchall()


# Khóa lịch, kiểm tra version và trạng thái trước khi cập nhật hoặc hủy.
def update_appointment(data,session_id):
    target=number(data,'id',1,2**31-1);version=number(data,'version',1,2**31-1)
    status=data.get('status')
    if status not in {'confirmed','completed','cancelled'}:raise OperationRejected('Trạng thái không hợp lệ.')
    if g.user and g.user['user_type']=='staff':
        if 'booking:manage' not in permissions():raise OperationRejected('Bạn không có quyền thực hiện yêu cầu này.',403)
        where,params=scope_filter('booking:manage','a.branch_id')
    else:
        if status!='cancelled':raise OperationRejected('Bạn không có quyền thực hiện yêu cầu này.',403)
        where,params=('a.customer_id=%s',(g.user['id'],)) if g.user else ('a.session_id=%s AND a.customer_id IS NULL',(session_id,))
    with cursor() as cur:
        cur.execute('SELECT a.* FROM appointment_requests a WHERE a.id=%s AND '+where+' FOR UPDATE',(target,*params));row=cur.fetchone()
        if not row:raise OperationRejected('Không tìm thấy lịch trong phạm vi được cấp.',404)
        if version!=row['version']:raise OperationRejected('Lịch đã thay đổi, hãy xem lại.',409)
        if status not in {'scheduled':{'confirmed','cancelled'},'confirmed':{'completed','cancelled'}}.get(row['status'],set()):
            raise OperationRejected('Không thể chuyển trạng thái này.',409)
        cur.execute('UPDATE appointment_requests SET status=%s,version=version+1 WHERE id=%s',(status,target))
        audit(cur,'appointment_update','appointment',target,before={'status':row['status']},after={'status':status},actor=g.user['id'] if g.user else None)
    return {'id':target,'status':status}
