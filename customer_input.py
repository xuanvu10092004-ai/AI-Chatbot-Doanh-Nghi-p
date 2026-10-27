# File này kiểm tra, staging và commit thông tin khách hàng từ form hoặc workbook.
from __future__ import annotations
import hashlib  # Tạo snapshot hồ sơ để phát hiện thay đổi giữa preview và commit.
import json  # Lưu dòng nhập, preview và kết quả đồng bộ trong các batch.
import re  # Kiểm tra email, điện thoại, mã khách và mã phiên bản.
import secrets  # Tạo mật khẩu vô hiệu hóa cho user khách mới.
from datetime import date, datetime  # Chuẩn hóa ngày sinh/ngày đăng ký và tính tuổi.
from pathlib import Path  # Chuẩn hóa đường dẫn workbook khách hàng.
from zoneinfo import ZoneInfo  # Lấy ngày hiện tại theo múi giờ Việt Nam.

from flask import g  # Lấy ID user đang tạo batch và ghi dữ liệu.
from werkzeug.security import generate_password_hash  # Tạo hash khi cần tạo user mới.

from db import cursor  # Đọc hồ sơ, khóa batch và lưu khách/đơn trong MySQL.
from security import permissions, audit  # Áp scope quyền và ghi nhật ký nhập khách.
from document_parser import clean, validate_file, ParseError  # Chuẩn hóa và xác thực workbook trước khi đọc.
from question_language import normalize  # So khớp header/trạng thái không phân biệt dấu.

FIELDS = {
 'customer_code':'Mã KH','full_name':'Họ và tên','gender':'Giới tính','birth_date':'Ngày sinh',
 'phone':'Số điện thoại','email':'Email','province':'Tỉnh/Thành phố','district':'Quận/Huyện',
 'address':'Địa chỉ','occupation':'Nghề nghiệp','lead_source':'Nguồn khách',
 'branch_code':'Chi nhánh phụ trách','interested_model':'Mẫu xe quan tâm',
 'payment_preference':'Hình thức thanh toán','registered_at':'Ngày đăng ký','status':'Trạng thái',
 'purchased_sku':'Mã SP','purchase_amount':'Giá trị mua (VNĐ)'}
REQUIRED = ('full_name','phone','email','branch_code','registered_at','status')
MAX_ROWS = 1000
WORKBOOK_HEADERS=['Mã KH','Họ và tên','Giới tính','Ngày sinh','Tuổi','Số điện thoại','Email','Tỉnh/Thành phố','Quận/Huyện','Địa chỉ','Nghề nghiệp','Nguồn khách','Chi nhánh phụ trách','Mẫu xe quan tâm','Hình thức thanh toán','Ngày đăng ký','Trạng thái','Mã SP đã mua','Giá trị mua (VNĐ)']


# Lỗi nhập khách có HTTP status để route trả thông báo phù hợp.
class CustomerInputError(ValueError):
    def __init__(self,message,status=400):super().__init__(message);self.status=status


def today():return datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()


def _date(value,label):
    if isinstance(value,datetime):return value.date().isoformat()
    if isinstance(value,date):return value.isoformat()
    text=clean(value)
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d/%m/%Y %H:%M:%S'):
        try:return datetime.strptime(text,fmt).date().isoformat()
        except ValueError:pass
    raise ValueError(label+' phải là ngày hợp lệ dạng dd/MM/yyyy.')


def _branch_allowed(code,branch_id):
    grant=permissions().get(code)
    return bool(grant) and (grant['scope']=='all' or grant['scope']=='branch' and grant['branch']==branch_id)


# Chuẩn hóa trường, ngày, email, điện thoại và kiểm tra điều kiện đơn hàng của từng dòng.
def normalize_row(raw):
    if not isinstance(raw,dict):raise CustomerInputError('Dòng dữ liệu không hợp lệ.')
    row={key:clean(raw.get(key)) for key in FIELDS}
    errors=[]
    for key in REQUIRED:
        if not row[key]:errors.append(FIELDS[key]+' bắt buộc.')
    limits={'full_name':150,'phone':20,'email':255,'province':60,'district':80,'address':255,'occupation':100,'lead_source':60}
    for key,limit in limits.items():
        if len(row[key])>limit:errors.append(FIELDS[key]+f' tối đa {limit} ký tự.')
    row['email']=row['email'].casefold();row['branch_code']=row['branch_code'].upper();row['customer_code']=row['customer_code'].upper()
    row['phone']=re.sub(r'[ .()-]','',row['phone'])
    if row['phone'] and not re.fullmatch(r'(?:0\d{9,10}|\+84\d{9,10})',row['phone']):errors.append('Số điện thoại không hợp lệ; cần giữ số 0 đầu.')
    if row['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@.]+',row['email']):errors.append('Email không hợp lệ.')
    if row['customer_code'] and not re.fullmatch(r'KH\d{4,10}',row['customer_code']):errors.append('Mã KH phải có dạng KH0001; để trống để cấp mã mới.')
    for key,allowed in [('gender',{'Nam','Nữ'}),('payment_preference',{'Trả thẳng','Trả góp'}),('status',{'Tiềm năng','Đang tư vấn','Đã mua','Ngừng liên hệ'})]:
        row[key]=next((value for value in allowed if normalize(value)==normalize(row[key])),row[key])
        if row[key] and row[key] not in allowed:errors.append(FIELDS[key]+' không thuộc danh sách hợp lệ.')
    for key in ('birth_date','registered_at'):
        if row[key]:
            try:
                row[key]=_date(raw.get(key),FIELDS[key])
                day=date.fromisoformat(row[key])
                if day>today() or (key=='birth_date' and today().year-day.year>120):errors.append(FIELDS[key]+' nằm ngoài khoảng hợp lệ.')
            except ValueError as error:errors.append(str(error))
    if row['purchased_sku']:
        row['purchased_sku']=row['purchased_sku'].upper()
        if not re.fullmatch(r'SP\d{3,10}',row['purchased_sku']):errors.append('Mã SP đã mua phải có dạng SP001.')
        try:
            amount=str(raw.get('purchase_amount','')).strip()
            if re.fullmatch(r'\d{1,3}(?:\.\d{3})+',amount):amount=amount.replace('.','')
            if not re.fullmatch(r'\d+(?:\.0+)?',amount):raise ValueError()
            row['purchase_amount']=int(float(amount))
            if not 0<row['purchase_amount']<=10000000000:raise ValueError()
        except (ValueError,OverflowError):errors.append('Giá trị mua phải là số nguyên VNĐ dương, không phải công thức thiếu kết quả.')
        if row['status']!='Đã mua':errors.append('Có mã SP đã mua thì trạng thái phải là Đã mua.')
    elif row['purchase_amount']:
        errors.append('Có giá trị mua thì cần mã SP đã mua.')
    elif row['status']=='Đã mua':
        errors.append('Khách Đã mua cần mã SP và giá trị mua để ghi nhận đơn hàng.')
    else:row['purchase_amount']=None
    return row,errors


# Kiểm tra tiêu đề bắt buộc, giới hạn dòng/cột rồi trả từng dòng theo tên trường chuẩn.
def read_customer_workbook(path):
    from openpyxl import load_workbook  # Đọc hoặc tạo workbook Excel.
    try:
        validate_file(Path(path),'xlsx')
        book=load_workbook(path,read_only=True,data_only=True,keep_links=False)
    except ParseError as error:raise CustomerInputError(str(error)) from None
    except Exception:raise CustomerInputError('Không đọc được file khách hàng. Hãy kiểm tra file gốc hoặc tải lại.') from None
    try:
        if 'Khach_hang' not in book.sheetnames:raise CustomerInputError('File cần sheet Khach_hang theo Excel mẫu.')
        sheet=book['Khach_hang']
        if sheet.max_row>MAX_ROWS+1:raise CustomerInputError(f'Mỗi lần đồng bộ tối đa {MAX_ROWS} khách hàng. Hãy chia file nhỏ hơn.')
        if sheet.max_column>30:raise CustomerInputError('Sheet khách hàng có quá nhiều cột.')
        iterator=sheet.iter_rows(values_only=True);header=list(next(iterator,()))
        if len(header)!=len(set(str(v) for v in header)):raise CustomerInputError('Tiêu đề cột bị trùng; hãy sửa trước khi tải lên.')
        mapping={normalize(label):key for key,label in FIELDS.items()}
        mapping['ma sp da mua']='purchased_sku'
        found={key for label in header if (key:=mapping.get(normalize(str(label))))}
        if not set(REQUIRED)<=found:raise CustomerInputError('File thiếu cột bắt buộc: '+', '.join(FIELDS[k] for k in REQUIRED if k not in found))
        rows=[]
        for values in iterator:
            if not any(v is not None and v!='' for v in values):continue
            rows.append({mapping[normalize(str(label))]:value for label,value in zip(header,values) if normalize(str(label)) in mapping})
        if not rows:raise CustomerInputError('Sheet Khach_hang không có khách hàng.')
        return rows
    finally:book.close()


def _existing(cur,row,lock=False):
    cur.execute('''SELECT u.id,u.email,u.full_name,u.phone,b.code AS branch_code,u.home_branch_id,
                   cp.customer_code,cp.gender,cp.birth_date,cp.province,cp.district,cp.address,cp.occupation,
                   cp.lead_source,p.model_name AS interested_model,cp.payment_preference,cp.registered_at,cp.status,s.version,s.deleted_at
                   FROM users u JOIN customer_profiles cp ON cp.user_id=u.id LEFT JOIN branches b ON b.id=u.home_branch_id
                   LEFT JOIN customer_admin_state s ON s.customer_id=u.id
                   LEFT JOIN products p ON p.id=cp.interested_product_id
                   WHERE u.user_type='customer' AND (cp.customer_code=%s OR u.email=%s)'''+(' FOR UPDATE' if lock else ''),(row['customer_code'],row['email']))
    matches=cur.fetchall()
    if len(matches)>1:raise ValueError('Email và mã KH không cùng hồ sơ; cần sửa trước khi lưu.')
    existing=matches[0] if matches else None
    if existing:
        from customer_service import require_customer_admin,CustomerError
        require_customer_admin()
        if existing['deleted_at']:raise CustomerError('Không sửa hồ sơ đã xóa; cần khôi phục trước.',409)
        if not _branch_allowed('customer:write',existing['home_branch_id']) or not _branch_allowed('customer:read',existing['home_branch_id']):raise ValueError('Dòng khách hàng không hợp lệ trong phạm vi được cấp.')
        if row['customer_code'] and row['customer_code']!=existing['customer_code']:raise ValueError('Email và mã KH không cùng hồ sơ; cần sửa trước khi lưu.')
        cur.execute('SELECT id FROM users WHERE email=%s AND id<>%s',(row['email'],existing['id']))
        if cur.fetchone():raise ValueError('Email không thể sử dụng cho hồ sơ này.')
    else:
        cur.execute('SELECT id FROM users WHERE email=%s',(row['email'],))
        if cur.fetchone():raise ValueError('Email không thể sử dụng cho hồ sơ này.')
    return existing


def preview_rows(cur,rows,lock=False):
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_ROWS:raise CustomerInputError(f'Bản nháp phải có từ 1 đến {MAX_ROWS} khách hàng.')
    result=[];seen_emails=set();seen_codes=set()
    for number,raw in enumerate(rows,1):
        row,errors=normalize_row(raw)
        purchase_missing='Khách Đã mua cần mã SP và giá trị mua để ghi nhận đơn hàng.'
        if purchase_missing in errors and not row['purchased_sku'] and not row['purchase_amount']:
            try:
                existing_profile=_existing(cur,row,lock)
                if existing_profile and existing_profile['status']=='Đã mua':
                    errors.remove(purchase_missing);row['purchase_amount']=None
            except ValueError as error:
                from customer_service import CustomerError
                if isinstance(error,CustomerError):raise
                errors.append(str(error))
        item={'row':number,'data':row,'errors':errors,'action':'create','changes':{},'before':None,'order_action':None}
        if row['birth_date'] and not errors:
            birthday=date.fromisoformat(row['birth_date']);now=today()
            item['age']=now.year-birthday.year-((now.month,now.day)<(birthday.month,birthday.day))
        if row['email'] in seen_emails:errors.append('Email trùng trong cùng file.')
        if row['customer_code'] and row['customer_code'] in seen_codes:errors.append('Mã KH trùng trong cùng file.')
        seen_emails.add(row['email']);seen_codes.add(row['customer_code'])
        if not errors:
            try:
                existing=_existing(cur,row,lock)
                cur.execute('SELECT id FROM branches WHERE code=%s',(row['branch_code'],));branch=cur.fetchone()
                if not branch or not _branch_allowed('customer:write',branch['id']):raise ValueError('Chi nhánh không hợp lệ trong phạm vi được cấp.')
                item['branch_id']=branch['id']
                product_id=None
                if row['interested_model']:
                    cur.execute('SELECT id,model_name FROM products WHERE model_name=%s',(row['interested_model'],));product=cur.fetchone()
                    if not product:
                        from question_language import product_pattern  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
                        pattern=product_pattern(row['interested_model'])
                        if pattern:
                            cur.execute('SELECT id,model_name FROM products WHERE model_name LIKE %s LIMIT 3',(pattern,));matches=cur.fetchall()
                            if len(matches)==1:product=matches[0]
                    if not product:raise ValueError('Mẫu xe quan tâm không có trong danh mục; cần chọn đúng tên.')
                    product_id=product['id'];row['interested_model']=product['model_name']
                item['product_id']=product_id
                item['before']=existing
                if existing:
                    item['action']='update';item['customer_id']=existing['id']
                    item['data']['customer_code']=existing['customer_code']
                    for key,value in row.items():
                        if key in existing and clean(existing[key])!=clean(value):item['changes'][key]={'before':clean(existing[key]),'after':value}
                if row['purchased_sku']:
                    if not _branch_allowed('order:write',branch['id']):raise ValueError('Chưa có quyền tạo đơn tại chi nhánh này.')
                    variant_id=int(row['purchased_sku'][2:])
                    cur.execute('SELECT id,variant_name FROM product_variants WHERE id=%s',(variant_id,));variant=cur.fetchone()
                    if not variant:raise ValueError('Mã SP đã mua không có trong danh mục.')
                    item['variant_id']=variant_id;item['variant_name']=variant['variant_name'];item['order_action']='create_pending'
                    if existing:
                        cur.execute('''SELECT o.id FROM orders o JOIN order_items oi ON oi.order_id=o.id
                                       WHERE o.customer_id=%s AND o.branch_id=%s AND oi.variant_id=%s
                                       AND oi.quantity=1 AND oi.unit_price=%s AND o.status<>'cancelled' ORDER BY o.id LIMIT 1''',
                                    (existing['id'],branch['id'],variant_id,row['purchase_amount']))
                        order=cur.fetchone()
                        if order:item['order_action']='existing';item['order_id']=order['id']
                item['snapshot']=hashlib.sha256(json.dumps(existing,default=str,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            except ValueError as error:
                from customer_service import CustomerError
                if isinstance(error,CustomerError):raise
                errors.append(str(error))
        result.append(item)
    return result


def _batch(cur,batch_id,lock=False):
    cur.execute('SELECT * FROM customer_input_batches WHERE id=%s AND created_by=%s'+(' FOR UPDATE' if lock else ''),(batch_id,g.user['id']))
    batch=cur.fetchone()
    if not batch:raise CustomerInputError('Không tìm thấy bản nháp trong phạm vi được xem.',404)
    if batch['status']!='draft':
        for row in json.loads(batch['rows_json']):
            cur.execute('SELECT id FROM branches WHERE code=%s',(row['branch_code'],));branch=cur.fetchone()
            if not branch or not _branch_allowed('customer:write',branch['id']) or not _branch_allowed('customer:read',branch['id']):
                raise CustomerInputError('Không tìm thấy bản nháp trong phạm vi được xem.',404)
    return batch


# Lưu bản nháp cùng snapshot xem trước; chưa tạo user hoặc đơn hàng ở bước này.
def stage(rows,document_id=None,chat_session_id=None):
    with cursor() as cur:
        preview=preview_rows(cur,rows)
        canonical=[item['data'] for item in preview]
        cur.execute('INSERT INTO customer_input_batches(created_by,document_id,chat_session_id,rows_json,preview_json) VALUES(%s,%s,%s,%s,%s)',
                    (g.user['id'],document_id,chat_session_id,json.dumps(canonical,ensure_ascii=False),json.dumps(preview,default=str,ensure_ascii=False)))
        batch_id=cur.lastrowid
    return {'id':batch_id,'version':1,'status':'draft','rows':preview,'valid':all(not r['errors'] for r in preview),'fields':FIELDS}


# Đọc batch thuộc user hiện tại và tính lại preview nếu bản nháp còn ở trạng thái draft.
def get_batch(batch_id):
    with cursor() as cur:
        batch=_batch(cur,batch_id)
        rows=preview_rows(cur,json.loads(batch['rows_json'])) if batch['status']=='draft' else json.loads(batch['preview_json'])
        cur.execute('SELECT warnings_json FROM customer_import_sources WHERE batch_id=%s',(batch_id,));source=cur.fetchone()
    return {'id':batch['id'],'version':batch['version'],'status':batch['status'],'rows':rows,'valid':all(not r['errors'] for r in rows),'fields':FIELDS,'result':json.loads(batch['result_json']) if batch['result_json'] else None,'warnings':json.loads(source['warnings_json']) if source else [],'document_id':batch['document_id']}


def revise(batch_id,rows,version):
    with cursor() as cur:
        batch=_batch(cur,batch_id,True)
        if batch['status']!='draft' or version!=batch['version']:raise CustomerInputError('Bản nháp đã thay đổi. Hãy tải lại.',409)
        if batch['document_id']:
            from document_service import _load  # Kiểm thử upload, hiệu đính và xuất bản tài liệu.
            document=_load(cur,batch['document_id'],True)
            cur.execute('SELECT document_version FROM customer_import_sources WHERE batch_id=%s',(batch_id,));source=cur.fetchone()
            if source and source['document_version']!=document['version']:
                raise CustomerInputError('File đã thay đổi. Hãy tạo lại bản xem trước từ file mới.',409)
        preview=preview_rows(cur,rows)
        cur.execute('UPDATE customer_input_batches SET rows_json=%s,preview_json=%s,version=version+1 WHERE id=%s',
                    (json.dumps([r['data'] for r in preview],ensure_ascii=False),json.dumps(preview,default=str,ensure_ascii=False),batch_id))
    return get_batch(batch_id)


# Khóa batch, kiểm tra version/snapshot rồi ghi user, hồ sơ và đơn chờ duyệt theo transaction.
def commit(batch_id,version,confirmed):
    if confirmed is not True:raise CustomerInputError('Cần xác nhận hồ sơ thay đổi và đơn hàng dự kiến trước khi lưu.')
    with cursor() as cur:
        # Khóa bộ đếm mã KH và ghi cùng transaction để hai lượt commit không cấp trùng mã.
        cur.execute('SELECT version FROM rbac_meta WHERE id=1 FOR UPDATE');cur.fetchone()
        batch=_batch(cur,batch_id,True)
        if batch['status']=='committed':return json.loads(batch['result_json'])
        if batch['status']!='draft' or version!=batch['version']:raise CustomerInputError('Bản nháp đã thay đổi. Hãy tải lại.',409)
        if batch['document_id']:
            from document_service import _load  # Kiểm thử upload, hiệu đính và xuất bản tài liệu.
            document=_load(cur,batch['document_id'],True)
            cur.execute('SELECT document_version FROM customer_import_sources WHERE batch_id=%s',(batch_id,));source=cur.fetchone()
            if source and source['document_version']!=document['version']:
                raise CustomerInputError('File đã thay đổi. Hãy tạo lại bản xem trước từ file mới.',409)
        preview=preview_rows(cur,json.loads(batch['rows_json']),lock=True)
        prior=json.loads(batch['preview_json'])
        if any(item['errors'] for item in preview):raise CustomerInputError('Có dòng không hợp lệ; chưa lưu khách hàng hoặc đơn hàng nào.')
        if [r['snapshot'] for r in preview]!=[r.get('snapshot') for r in prior]:raise CustomerInputError('Hồ sơ đã thay đổi kể từ lần xem trước. Hãy kiểm tra lại bản nháp.',409)
        cur.execute("SELECT id FROM roles WHERE name='customer'");role_id=cur.fetchone()['id']
        cur.execute("SELECT customer_code FROM customer_profiles WHERE customer_code REGEXP '^KH[0-9]+$'")
        used=[int(r['customer_code'][2:]) for r in cur.fetchall()]+[int(r['data']['customer_code'][2:]) for r in preview if r['data']['customer_code']]
        next_code=max(used,default=0)+1
        outcome={'created':0,'updated':0,'orders_created':0,'customer_ids':[],'order_ids':[],'batch_id':batch_id,'document_id':batch['document_id']}
        for item in preview:
            row=item['data'];old=item['before'];user_id=old['id'] if old else None
            if not user_id:
                cur.execute('''INSERT INTO users(email,full_name,phone,user_type,home_branch_id,password_hash,is_active,must_change_password)
                               VALUES(%s,%s,%s,'customer',%s,%s,FALSE,TRUE)''',
                            (row['email'],row['full_name'],row['phone'],item['branch_id'],'!disabled:'+secrets.token_hex(32)))
                user_id=cur.lastrowid
                cur.execute('INSERT IGNORE INTO customer_admin_state(customer_id) VALUES(%s)',(user_id,))
                code=row['customer_code'] or f'KH{next_code:04d}'
                if not row['customer_code']:next_code+=1
                cur.execute('INSERT INTO customer_profiles(user_id,customer_code) VALUES(%s,%s)',(user_id,code))
                cur.execute('INSERT INTO user_roles(user_id,role_id,granted_by) VALUES(%s,%s,%s)',(user_id,role_id,g.user['id']))
                outcome['created']+=1
            else:
                cur.execute('UPDATE users SET email=%s,full_name=%s,phone=%s,home_branch_id=%s WHERE id=%s',
                            (row['email'],row['full_name'],row['phone'],item['branch_id'],user_id));outcome['updated']+=1
            cur.execute('''UPDATE customer_profiles SET gender=%s,birth_date=%s,province=%s,district=%s,address=%s,
                           occupation=%s,lead_source=%s,interested_product_id=%s,payment_preference=%s,registered_at=%s,status=%s WHERE user_id=%s''',
                        (row['gender'] or None,row['birth_date'] or None,row['province'] or None,row['district'] or None,row['address'] or None,
                         row['occupation'] or None,row['lead_source'] or None,item['product_id'],row['payment_preference'] or None,row['registered_at'],row['status'],user_id))
            if item['order_action']=='create_pending':
                cur.execute("INSERT INTO orders(branch_id,customer_id,created_by,status) VALUES(%s,%s,%s,'pending')",(item['branch_id'],user_id,g.user['id']))
                order_id=cur.lastrowid
                cur.execute('INSERT INTO order_items(order_id,variant_id,quantity,unit_price) VALUES(%s,%s,1,%s)',(order_id,item['variant_id'],row['purchase_amount']))
                outcome['orders_created']+=1;outcome['order_ids'].append(order_id)
            outcome['customer_ids'].append(user_id)
            if batch['document_id']:
                cur.execute('INSERT INTO customer_import_rows(batch_id,customer_id,row_number,action) VALUES(%s,%s,%s,%s)',(batch_id,user_id,item['row'],item['action']))
            audit(cur,'customer_input_'+item['action'],'user',user_id,before=old,after={'full_name':row['full_name'],'branch_id':item['branch_id'],'batch_id':batch_id},actor=g.user['id'])
        cur.execute("UPDATE customer_input_batches SET status='committed',result_json=%s,version=version+1 WHERE id=%s",(json.dumps(outcome),batch_id))
    from excel_sync import sync_after_commit  # Đọc hoặc ghi workbook đồng bộ từ MySQL.
    outcome['excel_sync'] = sync_after_commit()
    return outcome
