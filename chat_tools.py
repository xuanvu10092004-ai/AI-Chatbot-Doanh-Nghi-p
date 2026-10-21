# File này nhận diện và thực thi các tool mà chatbot được phép gọi.
import json  # Đọc hoặc ghi dữ liệu JSON trong luồng xử lý của file.
import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import re  # Tìm và chuẩn hóa mẫu văn bản bằng biểu thức chính quy.
from datetime import datetime  # Tạo, so sánh hoặc định dạng ngày giờ.
from uuid import uuid4  # Tạo mã định danh ngẫu nhiên cho tài nguyên.
from flask import current_app,g  # Tạo request, response hoặc client Flask.
from db import cursor,transaction  # Mở cursor hoặc connection MySQL.
from security import permissions  # Dùng xác thực, permission hoặc audit của backend.
from access_control import authorize_intent,mark_audit_denied  # Dùng session, intent và quyền của chatbot.
from question_language import normalize  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
from operations_routes import OperationRejected,number  # Kiểm tra tham số số và trả lỗi tool theo nghiệp vụ.

DENIED='Tôi không thể hỗ trợ yêu cầu này.'
# name: (mô tả, permission, chỉ nhân viên, ghi dữ liệu, các trường nhận)
TOOLS={
 'stock_receive':('Nhập hàng','inventory:receive',True,True,'branch_id branch_code supplier reference_code notes items variant_id quantity'),
 'stock_list':('Lịch sử nhập hàng','inventory:receive',True,False,''),
 'catalog_save':('Thêm/sửa mẫu xe, phiên bản, giá và đời xe','product:manage',True,True,'id product_id model_name variant_name segment engine_cc list_price model_year lifecycle version'),
 'catalog_list':('Xem danh mục xe để lấy ID và phiên bản','product:manage',True,False,''),
 'booking_create':('Đặt lịch sửa xe cho khách hàng','booking:create',True,True,'branch_id branch_code customer_id scheduled_at service_type vehicle_description license_plate notes'),
 'booking_update':('Xác nhận/hoàn tất/hủy lịch sửa xe','booking:read',True,True,'id status version'),
 'booking_list':('Xem lịch sửa chữa','booking:read',True,False,''),
 'appointment_create':('Đặt lịch bảo dưỡng hoặc tư vấn','kb:public:read',False,True,'branch_id branch_code kind full_name phone email scheduled_at notes'),
 'appointment_list':('Xem lịch bảo dưỡng và tư vấn của mình hoặc trong phạm vi nhân viên','booking:read',False,False,''),
 'appointment_update':('Hủy lịch của mình; nhân viên xác nhận/hoàn tất lịch tư vấn/bảo dưỡng','booking:read',False,True,'id status version'),
 'dashboard_read':('Xem chỉ tiêu tổng quan: orders, inventory, customers, revenue-month, revenue-branch, inventory-branch, customer-status, customer-source, bestsellers, profit','dashboard:view',True,False,'widget'),
 'users_list':('Danh sách tài khoản','user:manage',True,False,''),
 'user_save':('Thêm/sửa tài khoản, khóa/mở khóa; mật khẩu nhập qua ô bảo mật khi xác nhận','user:manage',True,True,'id email full_name home_branch_id is_active roles lock unlock'),
 'user_password':('Đặt lại mật khẩu tài khoản qua ô bảo mật, không ghi mật khẩu vào hội thoại','user:manage',True,True,'id'),
 'roles_list':('Danh sách vai trò và phạm vi quyền','rbac:manage',True,False,''),
 'role_save':('Thêm/sửa vai trò và ma trận permissions[{permission_id,data_scope}]','rbac:manage',True,True,'id name description landing_path priority is_active permissions clone_id'),
 'role_delete':('Xóa vai trò không sử dụng','rbac:manage',True,True,'id'),
 'permissions_list':('Danh mục quyền','rbac:manage',True,False,''),
 'permission_save':('Sửa mô tả quyền','rbac:manage',True,True,'id description'),
 'assignment_save':('Gán vai trò cho tài khoản: id là tài khoản; roles[{role_id,scope_branch_id,expires_at}]','user:manage',True,True,'id roles'),
 'assignment_delete':('Gỡ một vai trò khỏi tài khoản','user:manage',True,True,'id role_id'),
 'audit_list':('Xem nhật ký hệ thống','audit:read',True,False,''),
 'documents_list':('Danh sách tài liệu và ID','document:manage',True,False,''),
 'document_review':('Hiệu đính tài liệu với nội dung/ghi chú đã đối chiếu','document:manage',True,True,'id title content notes version'),
 'document_publish':('Đưa tài liệu đã hiệu đính vào kho tri thức','document:manage',True,True,'id version'),
 'orders_list':('Danh sách đơn hàng','order:read',True,False,''),
 'invoice_export':('Xuất chứng từ PDF của đơn hàng','invoice:export',True,False,'id'),
}
REQUIRED={
 'stock_receive':('branch_id','supplier','items'),
 'catalog_save':('model_name','variant_name','segment','engine_cc','list_price'),
 'booking_create':('branch_id','customer_id','scheduled_at','service_type','vehicle_description'),
 'appointment_create':('branch_id','kind','scheduled_at'),
 'booking_update':('id','status'),'appointment_update':('id','status'),
 'dashboard_read':('widget',),'user_save':('full_name',),'user_password':('id',),'role_save':('name',),
 'role_delete':('id',),'permission_save':('id','description'),
 'assignment_save':('id','roles'),'assignment_delete':('id','role_id'),
 'document_review':('id','title','content'),'document_publish':('id',),'invoice_export':('id',),
}
ALIASES={'chi nhanh':'branch_code','nha cung cap':'supplier','chung tu':'reference_code','ma chung tu':'reference_code',
 'ma sp':'variant_id','so luong':'quantity','ho ten':'full_name','ho va ten':'full_name','sdt':'phone','dien thoai':'phone',
 'khach hang':'customer_id','ma kh':'customer_id','ngay gio':'scheduled_at','ngay hen':'scheduled_at','thoi gian':'scheduled_at',
 'dich vu':'service_type','xe':'vehicle_description','bien so':'license_plate','ghi chu':'notes','gia':'list_price',
 'gia niem yet':'list_price','ten mau':'model_name','mau xe':'model_name','phien ban':'variant_name',
 'phan khuc':'segment','dung tich':'engine_cc','doi xe':'model_year','nam doi':'model_year','trang thai':'status',
 'email':'email','id':'id','ten vai tro':'name','mo ta':'description'}


def staff():return bool(g.user and g.user.get('user_type')=='staff')


def available_tools():
    grants=permissions()
    return {k:v for k,v in TOOLS.items() if v[1] in grants and (not v[2] or staff())
            and (v[1]!='rbac:manage' or grants[v[1]]['scope']=='all')}


def allowed(name,session_id):
    result=authorize_intent(session_id,g.user['id'] if g.user else None,'tool_'+name)
    ok=result['allowed'] and name in available_tools()
    if not ok and result['allowed']:mark_audit_denied(result['audit_id'],'Công cụ không thuộc loại tài khoản được phép')
    return ok,result['audit_id']


def endpoint(name,**kwargs):
    """Dùng lại handler và decorator backend, cùng request/session/transaction hiện tại."""
    response=current_app.make_response(current_app.view_functions[name](**kwargs))
    if response.status_code>=400:
        data=response.get_json(silent=True) or {}
        raise OperationRejected(data.get('message',DENIED),response.status_code)
    if response.mimetype=='application/pdf':
        response.close()
        return {'download_url':'/api/orders/'+str(kwargs['order_id'])+'/invoice.pdf'}
    return response.get_json()


def run(name,data,session_id):
    if name=='stock_receive':
        from stock_service import receive_stock  # Ghi phiếu nhập và cộng số lượng tồn.
        return receive_stock(data)
    if name=='stock_list':
        from stock_service import list_receipts  # Đọc phiếu nhập trong phạm vi chi nhánh.
        return {'rows':list_receipts()}
    if name=='catalog_save':return endpoint('save_vehicle',variant_id=data.get('id'),tool_data=data)
    if name=='booking_create':return endpoint('create_booking',tool_data=data)
    if name=='booking_update':return endpoint('update_booking',booking_id=data['id'],tool_data=data)
    if name=='appointment_create':
        from appointment_service import create_appointment  # Tạo lịch tư vấn/bảo dưỡng cho user hoặc khách.
        return create_appointment(data,session_id)
    if name=='appointment_list':
        from appointment_service import list_appointments  # Đọc lịch tư vấn/bảo dưỡng theo scope quyền.
        return {'rows':list_appointments()}
    if name=='appointment_update':
        from appointment_service import update_appointment  # Hủy hoặc chuyển trạng thái lịch hợp lệ.
        return update_appointment(data,session_id)
    if name=='dashboard_read':
        from dashboard_service import WIDGETS,widget_data  # Kiểm tra quyền widget trước khi truy vấn số liệu.
        if data['widget'] not in WIDGETS or not all(p in permissions() for p in WIDGETS[data['widget']][1]):
            raise OperationRejected(DENIED,403)
        return {'rows':widget_data(data['widget'])}
    read={'catalog_list':'catalog_list','booking_list':'booking_list','users_list':'users_list','roles_list':'roles_list',
          'permissions_list':'permission_list','audit_list':'audit_list','orders_list':'sales_orders_list'}
    if name in read:return endpoint(read[name])
    if name=='invoice_export':return endpoint('sales_invoice_export',order_id=data['id'])
    if name=='documents_list':
        from document_service import list_documents  # Lấy danh sách tài liệu được phép quản lý.
        return list_documents()
    if name.startswith('document_'):
        from document_service import save_review,publish_document  # Hiệu đính hoặc xuất bản bản đã kiểm tra.
        return (save_review if name=='document_review' else publish_document)(data['id'],{**data,'confirmed':True})
    from admin_service import mutate  # Lưu thay đổi user, role và permission qua service RBAC.
    kinds={'user_save':'user','user_password':'user','role_save':'role','role_delete':'role','permission_save':'permission',
           'assignment_save':'assignment','assignment_delete':'assignment'}
    return {'id':mutate(kinds[name],data.get('id'),data,'delete' if name.endswith('_delete') else 'save')}


def infer(question):
    q=normalize(question)
    q=re.sub(r'^(?:toi muon|hay|giup toi|vui long|cho toi)\s+','',q)
    rules=[('stock_list',r'^(?:xem )?lich su nhap (?:hang|kho)'),('stock_receive',r'^(?:toi muon |hay )?nhap (?:hang|kho)\b'),
       ('catalog_list',r'^(?:xem )?danh muc xe'),('catalog_save',r'^(?:them|tao|sua|doi|cap nhat) (?:mau xe|phien ban|gia xe|gia |doi xe)'),
       ('appointment_create',r'^(?:toi muon |hay )?dat lich (?:bao duong|tu van)'),('booking_create',r'^(?:toi muon )?dat lich sua'),
       ('appointment_list',r'^(?:xem )?(?:danh sach |cac )?lich (?:tu van|bao duong)'),
       ('booking_list',r'^(?:xem )?(?:danh sach |cac )?lich (?:hen|sua)'),
       ('appointment_update',r'^(?:huy|xac nhan|hoan tat|cap nhat) lich (?:tu van|bao duong)'),
       ('booking_update',r'^(?:huy|xac nhan|hoan tat|cap nhat) lich (?:hen|sua)'),
       ('users_list',r'^(?:xem )?danh sach tai khoan'),('roles_list',r'^(?:xem )?danh sach vai tro'),
       ('permissions_list',r'^(?:xem )?danh (?:sach|muc) quyen'),('user_save',r'^(?:them|tao|sua|cap nhat|khoa|mo khoa) tai khoan'),
       ('user_password',r'^(?:doi|dat lai|reset) mat khau tai khoan'),
       ('role_save',r'^(?:them|tao|sua|cap nhat) vai tro'),('role_delete',r'^xoa vai tro'),
       ('assignment_save',r'^(?:gan|cap) vai tro'),('assignment_delete',r'^(?:go|thu hoi) vai tro'),
       ('permission_save',r'^(?:sua|cap nhat) mo ta quyen'),('audit_list',r'^(?:xem )?nhat ky'),
       ('documents_list',r'^(?:xem )?danh sach (?:tai lieu|tep)'),('document_review',r'^(?:hieu dinh|sua noi dung) tai lieu'),
       ('document_publish',r'^(?:xuat ban|dua vao kho tri thuc) tai lieu'),('orders_list',r'^(?:xem )?danh sach don hang'),
       ('invoice_export',r'^xuat (?:hoa don|phieu|chung tu)'),('dashboard_read',r'^(?:xem )?tong quan\b')]
    return next((name for name,pattern in rules if re.search(pattern,q)),None)


# Chuẩn hóa đầu vào trong bước parse_args để các phép so khớp phía sau dùng cùng một dạng.
def parse_args(question,name):
    start=question.find('{')
    result={}
    if start>=0:
        try:
            parsed=json.loads(question[start:])
            if isinstance(parsed,dict):result=parsed
        except ValueError:pass
    body=question.split(':',1)[1] if ':' in question and not result else ''
    for part in re.split(r'[;\n]',body):
        if ':' not in part:continue
        label,value=part.split(':',1);key=ALIASES.get(normalize(label),normalize(label).replace(' ','_'))
        result[key]=value.strip()
    q=normalize(question)
    code=re.search(r'\b(nt01|nt02|cr01)\b',q)
    if code and 'branch_id' not in result:result.setdefault('branch_code',code.group(1).upper())
    sku=re.search(r'\bsp\s*(\d+)\b',q)
    if sku:result.setdefault('variant_id' if name=='stock_receive' else 'id',int(sku.group(1)))
    if 'id' not in result and name in {'booking_update','appointment_update','user_save','user_password','role_save','role_delete','permission_save','assignment_save','assignment_delete','document_review','document_publish','invoice_export'}:
        identifier=re.search(r'(?:#|\bid\s*[:=]?\s*|tai khoan\s+|vai tro\s+|tai lieu\s+|don\s+)(\d+)\b',q)
        if identifier:result['id']=int(identifier.group(1))
    if name=='stock_receive' and 'quantity' not in result:
        match=re.search(r'(\d+)\s*(?:xe|chiec)\b',q)
        if match:result['quantity']=int(match.group(1))
    if name=='stock_receive' and 'items' not in result:
        skus={int(m) for m in re.findall(r'\bsp\s*(\d+)\b',q)}
        if len(skus)>1:
            pairs={int(sku):int(quantity) for sku,quantity in re.findall(r'\bsp\s*(\d+)\s*[:=x×]\s*(\d+)\b',q)}
            pairs.update({int(sku):int(quantity) for quantity,sku in re.findall(r'\b(\d+)\s*(?:xe|chiec)\s+sp\s*(\d+)\b',q)})
            result.pop('variant_id',None);result.pop('quantity',None)
            if skus<=pairs.keys():result['items']=[{'variant_id':sku,'quantity':pairs[sku]} for sku in sorted(skus)]
    if name.endswith('_update'):
        if q.startswith('huy'):result.setdefault('status','cancelled')
        elif q.startswith('xac nhan'):result.setdefault('status','confirmed')
        elif q.startswith('hoan tat'):result.setdefault('status','completed')
    if name=='appointment_create':result['kind']='consultation' if 'tu van' in q else 'maintenance'
    if name=='user_save':
        if q.startswith('mo khoa'):result['unlock']=True
        elif q.startswith('khoa'):result['lock']=True
    if name=='dashboard_read':result.setdefault('widget','inventory' if 'ton kho' in q else 'customers' if 'khach' in q else 'orders')
    return result


def model_args(question,name):
    """Chỉ dùng khi lệnh đã được nhận diện và người dùng có quyền công cụ đó."""
    if not os.getenv('GROQ_API_KEY'):return None
    import ai_service  # Dùng cấu hình model/client Groq dùng chung.
    if ai_service.client is None:
        from groq import Groq  # Tạo client khi arguments của model được yêu cầu lần đầu.
        ai_service.client=Groq(api_key=os.environ['GROQ_API_KEY'],timeout=15,max_retries=0)
    schema={'tool':name,'description':TOOLS[name][0],'fields':TOOLS[name][4].split(),'required':REQUIRED.get(name,())}
    message='Chuyển lệnh tiếng Việt thành JSON arguments, chỉ những trường cho phép. Không tạo SQL. Không suy đoán ID, ngày, tên, giá hoặc số lượng thiếu. branch_code dùng NT01/NT02/CR01. scheduled_at yyyy-mm-ddTHH:mm, múi giờ Việt Nam. items=[{variant_id,quantity}]. Không nhận password, quyền truy cập hoặc user_id để giả danh. Nếu thiếu thông tin, trả những trường đã biết. Schema: '+json.dumps(schema,ensure_ascii=False)
    out=ai_service.client.chat.completions.create(model=ai_service.MODEL,messages=[{'role':'system','content':message},{'role':'user','content':question}],temperature=0,max_tokens=1000,response_format={'type':'json_object'})
    data=json.loads(out.choices[0].message.content)
    return data.get('arguments',data) if isinstance(data,dict) else None


def prepare(name,raw):
    if not isinstance(raw,dict):raise OperationRejected('Tham số lệnh phải là một đối tượng.')
    if any(k.lower() in {'password','password_hash','user_id','created_by','actor','sql','url','endpoint','_rbac_version'} for k in raw):
        raise OperationRejected('Không nhận mật khẩu, danh tính hoặc câu SQL trong công cụ chat.')
    data={k:v for k,v in raw.items() if k in TOOLS[name][4].split()}
    for key in ('id','branch_id','variant_id','customer_id','product_id','engine_cc','model_year','quantity','role_id','home_branch_id'):
        if key in data and data[key] not in (None,''):
            value=str(data[key]).strip();value=re.sub(r'^(?:SP|KH)','',value,flags=re.I)
            data[key]=number({key:value},key,1,2**31-1)
    if 'list_price' in data:data['list_price']=number({'list_price':str(data['list_price']).replace('.','')},'list_price',1,10_000_000_000)
    if 'branch_code' in data:
        with cursor() as cur:
            cur.execute('SELECT id FROM branches WHERE code=%s',(str(data.pop('branch_code')).upper(),));row=cur.fetchone()
        if not row:raise OperationRejected('Chi nhánh không hợp lệ.')
        data['branch_id']=row['id']
    if name in {'stock_receive','booking_create'} and 'branch_id' not in data:
        code='inventory:receive' if name=='stock_receive' else 'booking:create'
        grant=permissions()[code]
        if grant['scope']=='branch':data['branch_id']=grant['branch']
    if name=='stock_receive':
        if 'items' not in data and 'variant_id' in data and 'quantity' in data:data['items']=[{'variant_id':data.pop('variant_id'),'quantity':data.pop('quantity')}]
        data.setdefault('reference_code','CHAT-'+uuid4().hex.upper());data.setdefault('notes','Nhập qua trợ lý AI')
        grant=permissions()['inventory:receive']
        if 'branch_id' in data and grant['scope']!='all' and (grant['scope']!='branch' or data['branch_id']!=grant['branch']):raise OperationRejected(DENIED,403)
    if name=='catalog_save' and data.get('id'):
        row=next((r for r in endpoint('catalog_list')['rows'] if r['id']==data['id']),None)
        if not row:raise OperationRejected('Không tìm thấy xe trong phạm vi được cấp.',404)
        data={**row,**data,'version':row['version']};data.pop('product_id',None)
    if name in {'booking_update','appointment_update'}:
        rows=run('booking_list' if name=='booking_update' else 'appointment_list',{},None)['rows']
        row=next((r for r in rows if r['id']==data.get('id')),None)
        if not row:raise OperationRejected('Không tìm thấy lịch trong phạm vi được cấp.',404)
        data['version']=row['version']
        if data.get('status')!='cancelled' and 'booking:manage' not in permissions():raise OperationRejected(DENIED,403)
    if name.startswith('document_') and name!='documents_list' and data.get('id'):
        from document_service import get_document  # Đọc version trước khi tạo lệnh hiệu đính.
        row=get_document(data['id']);data['version']=row['version']
    if name=='user_save' and data.get('id'):
        row=next((r for r in endpoint('users_list')['rows'] if r['id']==data['id']),None)
        if not row:raise OperationRejected('Không tìm thấy tài khoản trong phạm vi được cấp.',404)
        data.setdefault('full_name',row['full_name'])
    if name=='role_save' and data.get('id'):
        row=next((r for r in endpoint('roles_list')['rows'] if r['id']==data['id']),None)
        if not row:raise OperationRejected('Không tìm thấy vai trò.',404)
        data.setdefault('name',row['name'])
    if name in {'user_save','user_password','role_save','role_delete','permission_save','assignment_save','assignment_delete'}:
        with cursor() as cur:cur.execute('SELECT version FROM rbac_meta WHERE id=1');data['_rbac_version']=cur.fetchone()['version']
    if name=='user_save' and not data.get('id') and not data.get('email'):
        raise OperationRejected('Cần bổ sung email cho tài khoản mới. Mật khẩu sẽ nhập trong ô bảo mật ở bước xác nhận.')
    if name=='appointment_create' and g.user and g.user['user_type']=='customer':
        data.update(full_name=g.user['full_name'],email=g.user['email']);data.setdefault('phone',g.user['phone'])
    for key in ('scheduled_at',):
        if key in data:
            for fmt in ('%d/%m/%Y %H:%M','%d/%m/%Y %Hh%M'):
                try:data[key]=datetime.strptime(data[key],fmt).isoformat();break
                except (ValueError,TypeError):pass
    if data.get('service_type') in {'bảo dưỡng','bao duong'}:data['service_type']='maintenance'
    for key,mapping in [('segment',{'xe ga':'tay_ga','xe so':'xe_so','xe con':'con_tay'}),('lifecycle',{'doi cu':'previous','doi moi':'current','ngung kinh doanh':'discontinued'})]:
        if key in data:data[key]=mapping.get(normalize(str(data[key])),data[key])
    missing=[key for key in REQUIRED.get(name,()) if data.get(key) in (None,'',[])]
    if name=='appointment_create' and not data.get('full_name'):missing.append('full_name')
    if name=='appointment_create' and not data.get('phone'):missing.append('phone')
    if missing:raise OperationRejected('Cần bổ sung: '+', '.join(missing)+'. Nhập các trường theo “Tên trường: giá trị”, ngăn bằng dấu chấm phẩy.')
    return data


def reply_result(name,result):
    return {'type':'tool','answer':TOOLS[name][0]+': đã thực hiện.'+(' '+result.get('message','') if isinstance(result,dict) else ''),
            'rows':result.get('rows',[]) if isinstance(result,dict) else [],'result':result,
            'download_url':result.get('download_url') if isinstance(result,dict) else None}


def confirm_action(action_id,session_id,confirmation,secret=None):
    with transaction():
        with cursor() as cur:
            cur.execute('''SELECT *,created_at<DATE_SUB(NOW(),INTERVAL 30 MINUTE) AS expired FROM chat_action_drafts
                        WHERE id=%s AND session_id=%s AND user_id <=> %s FOR UPDATE''',(action_id,session_id,g.user['id'] if g.user else None))
            row=cur.fetchone()
        if not row:raise OperationRejected('Không tìm thấy lệnh trong phiên hiện tại.',404)
        name=row['tool_name']
        ok,_=allowed(name,session_id)
        if not ok:raise OperationRejected(DENIED,403)
        if row['status']=='committed':return reply_result(name,json.loads(row['result_json']))
        if row['expired'] or row['status']!='draft':raise OperationRejected('Lệnh đã hết hạn hoặc bị hủy. Hãy nhập lại.',409)
        if confirmation and confirmation!=(row['id'],row['version']):raise OperationRejected('Bản xem trước đã thay đổi.',409)
        data=json.loads(row['arguments_json'])
        if '_rbac_version' in data:
            with cursor() as cur:cur.execute('SELECT version FROM rbac_meta WHERE id=1 FOR UPDATE');version=cur.fetchone()['version']
            if data.pop('_rbac_version')!=version:raise OperationRejected('Quyền hoặc tài khoản đã thay đổi. Hãy tạo lại lệnh để xem trước.',409)
        if name=='user_password' or name=='user_save' and not data.get('id'):
            if not isinstance(secret,str) or not 10<=len(secret)<=256:
                raise OperationRejected('Nhập mật khẩu tạm 10–256 ký tự trong ô bảo mật của bản xem trước.')
            data['password']=secret
        result=run(name,data,session_id)
        with cursor() as cur:
            cur.execute("UPDATE chat_action_drafts SET status='committed',result_json=%s,version=version+1 WHERE id=%s",(json.dumps(result,default=str,ensure_ascii=False),row['id']))
        return reply_result(name,result)


def handle_tool_chat(question,session_id,confirmation=None,secret=None):
    q=normalize(question)
    if q in {'tro giup','cac chuc nang','ban lam duoc gi','huong dan lenh'}:
        items=[v[0] for v in available_tools().values()]
        prefix='Bạn đang dùng chế độ nhân viên, công cụ được lọc theo quyền và chi nhánh. ' if staff() else 'Bạn đang dùng chế độ khách: tra giá xe, đặt lịch bảo dưỡng hoặc tư vấn. '
        return {'type':'tool','answer':prefix+'Các lệnh khả dụng: '+ '; '.join(items)+'. Lệnh ghi cần xem trước và xác nhận.','rows':[]}
    confirm=re.fullmatch(r'xac nhan lenh\s*#?(\d+)',q)
    cancel=re.fullmatch(r'huy lenh\s*#?(\d+)',q)
    audit_id=None
    try:
        file_import=re.search(r'^(?:dong bo|nhap|cap nhat).*khach.*(?:tai lieu|file|tep)\s*#?(\d+)\b',q)
        if file_import:
            authorization=authorize_intent(session_id,g.user['id'] if g.user else None,'add_customer')
            if not authorization['allowed'] or not staff() or 'document:manage' not in permissions():
                mark_audit_denied(authorization['audit_id'],'Không có quyền nhập file khách hàng')
                return {'type':'tool','answer':DENIED,'access_denied':True,'rows':[]}
            from customer_file_import import stage_document  # Chuyển file thành bản nháp nhập khách.
            from customer_input import CustomerInputError  # Trả lỗi kiểm tra batch nhập khách.
            try:batch=stage_document(int(file_import.group(1)),session_id)
            except CustomerInputError as error:return {'type':'customer-input','answer':str(error),'rows':[]}
            if batch['status']=='committed':return {'type':'customer-input','answer':'Danh sách này đã được đồng bộ.','result':batch['result'],'rows':[]}
            return {'type':'customer-input','answer':'Đã đọc danh sách khách. Hãy đối chiếu toàn bộ dòng rồi xác nhận lưu.','customer_draft':batch,'rows':[]}
        if confirm:return confirm_action(int(confirm.group(1)),session_id,confirmation,secret)
        if cancel:
            with cursor() as cur:cur.execute("UPDATE chat_action_drafts SET status='cancelled' WHERE id=%s AND session_id=%s AND user_id <=> %s AND status='draft'",(int(cancel.group(1)),session_id,g.user['id'] if g.user else None))
            return {'type':'tool','answer':'Đã xử lý hủy lệnh trong phiên hiện tại.','rows':[]}
        name=infer(question)
        if not name:return None
        ok,audit_id=allowed(name,session_id)
        if not ok:return {'type':'tool','answer':DENIED,'access_denied':True,'rows':[]}
        if re.search(r"\b(?:password|mat khau)[\"']?\s*[:=]",q):
            return {'type':'tool','answer':'Không nhập mật khẩu vào câu lệnh. Hãy tạo lệnh tài khoản trước, sau đó nhập mật khẩu trong ô bảo mật ở bước xác nhận.','rows':[]}
        raw=parse_args(question,name)
        try:data=prepare(name,raw)
        except OperationRejected as error:
            if error.status!=400 or not os.getenv('GROQ_API_KEY'):raise
            guessed=model_args(question,name)
            if not guessed:raise error
            data=prepare(name,guessed)
        if name=='stock_receive':
            mentioned={int(m) for m in re.findall(r'\bsp\s*(\d+)\b',q)}
            actual={number(item,'variant_id',1,2**31-1) for item in data['items'] if isinstance(item,dict)}
            if not mentioned<=actual:raise OperationRejected('Bản nhập còn thiếu mã SP bạn đã nêu. Hãy nhập từng cặp “SP014: 3; SP015: 2”.')
        if not TOOLS[name][3]:return reply_result(name,run(name,data,session_id))
        with cursor() as cur:
            cur.execute('INSERT INTO chat_action_drafts(session_id,user_id,tool_name,arguments_json) VALUES(%s,%s,%s,%s)',(session_id,g.user['id'] if g.user else None,name,json.dumps(data,ensure_ascii=False,default=str)))
            action_id=cur.lastrowid
        public={k:v for k,v in data.items() if not k.startswith('_')}
        return {'type':'tool','answer':'Bản xem trước '+TOOLS[name][0]+'. Chưa ghi thay đổi. Kiểm tra thông tin rồi xác nhận.',
                'action_draft':{'id':action_id,'version':1,'title':TOOLS[name][0],'arguments':public,'requires_password':name=='user_password' or name=='user_save' and not data.get('id')},'rows':[]}
    except Exception as error:
        from admin_service import AdminRejected  # Nhận diện lỗi thay đổi RBAC bị từ chối.
        from document_service import DocumentError  # Nhận diện lỗi quyền/trạng thái tài liệu.
        if isinstance(error,(OperationRejected,AdminRejected,DocumentError)):
            denied=getattr(error,'status',400) in {403,404}
            if denied:
                if audit_id:mark_audit_denied(audit_id,'Quyền, loại tài khoản hoặc phạm vi công cụ không hợp lệ')
                else:
                    with cursor() as cur:
                        cur.execute("INSERT INTO chatbot_audit_log(session_id,user_id,decision,reason) VALUES(%s,%s,'denied',%s)",(session_id,g.user['id'] if g.user else None,'Xác nhận công cụ bị từ chối; không thay đổi dữ liệu'))
            return {'type':'tool','answer':DENIED if denied else str(error),'access_denied':denied,'rows':[]}
        raise
