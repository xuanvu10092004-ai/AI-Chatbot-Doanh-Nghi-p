# Nhận lệnh nhập khách qua chat, kiểm tra quyền và cập nhật bản nháp cho user hiện tại.
import json  # Đọc kết quả batch đã lưu trong MySQL.
import re  # Tách trường và nhận diện lệnh nhập/xác nhận/hủy.
from flask import g  # Lấy user sở hữu bản nháp trong request hiện tại.
from db import cursor  # Tìm batch draft đang mở theo session và user.
from security import permissions  # Áp scope customer:write khi khởi tạo bản nháp.
from question_language import normalize, product_pattern  # Chuẩn hóa lệnh và nhận diện tên xe trong câu trả lời.
from customer_input import FIELDS, REQUIRED, today, stage, get_batch, revise, commit, CustomerInputError, normalize_row, _existing  # Dùng lại kiểm tra và lifecycle batch khách.
from access_control import authorize_intent  # Kiểm tra quyền nhập khách trước khi xử lý câu hỏi.
from excel_sync import sync_after_commit  # Đồng bộ workbook sau khi commit thành công.


# Chuẩn hóa đầu vào trong bước parse_customer_values để các phép so khớp phía sau dùng cùng một dạng.
def parse_customer_values(text):
    """Tách các trường có nhãn hoặc tên, email, điện thoại; giữ nguyên địa chỉ."""
    labels={normalize(label):key for key,label in FIELDS.items()}
    labels.update({'ten':'full_name','ho ten':'full_name','sdt':'phone','dien thoai':'phone',
                   'chi nhanh':'branch_code','ma kh':'customer_code','ma sp':'purchased_sku',
                   'ma sp da mua':'purchased_sku','gia tri mua':'purchase_amount'})
    result={}
    for part in re.split(r'[;\n]|,\s*(?=[^,:;\n]{2,35}:)',text):
        if ':' in part:
            label,value=part.split(':',1)
            if (key:=labels.get(normalize(label))):result[key]=value.strip()
    if result:return result
    parts=[p.strip(' .') for p in text.split(',') if p.strip()]
    if len(parts)<2:return result
    leftovers=[]
    for part in parts:
        if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@.]+',part):result['email']=part
        elif re.fullmatch(r'(?:0\d{9,10}|\+84\d{9,10})',re.sub(r'[ .()-]','',part)):result['phone']=part
        else:leftovers.append(part)
    if result and leftovers:
        result['full_name']=leftovers[0]
        if len(leftovers)>1:result['address']=', '.join(leftovers[1:])
    return result


def handle_customer_chat(question,session_id,confirmation=None):
    from customer_service import CustomerError
    try:return _handle_customer_chat(question,session_id,confirmation)
    except CustomerError as error:
        denied=error.status in {403,404}
        if denied:
            from access_control import mark_audit_denied
            authorization=authorize_intent(session_id,g.user['id'] if g.user else None,'add_customer')
            mark_audit_denied(authorization['audit_id'],'Không có quyền quản trị hồ sơ khách hàng')
        return {'type':'customer-input','answer':'Tôi không thể hỗ trợ yêu cầu này.' if denied else str(error),'access_denied':denied,'rows':[]}


def _handle_customer_chat(question,session_id,confirmation=None):
    q=normalize(question)
    if re.match(r'^(?:sua|cap nhat) khach hang\b',q):
        from customer_service import require_customer_admin
        require_customer_admin()
    quick=bool(re.match(r'^(?:them|tao|nhap) (?:nhanh )?khach (?:hang )?(?:mua xe|da dong y mua)\b',q))
    starting=quick or bool(re.match(r'^(?:them|tao|nhap|sua|cap nhat) (?:(?:mot|nhanh) )?khach hang\b',q))
    with cursor() as cur:
        cur.execute("SELECT id FROM customer_input_batches WHERE chat_session_id=%s AND created_by=%s AND status='draft' ORDER BY id DESC LIMIT 1",(session_id,g.user['id'] if g.user else None))
        pending=cur.fetchone()
    if not starting and not pending:return None
    # Một câu hỏi mới không được biến thành giá trị của trường còn thiếu.
    values=parse_customer_values(question)
    if pending and not starting and not values and (product_pattern(question) or re.search(
        r'\b(?:ton kho|het hang|con hang|san pham nao|chi nhanh nao|hien tai|bao nhieu|tong|so sanh|thong so|khuyen mai|don hang|gia von|gia xe|quy trinh|bao duong|chinh sach|danh sach)\b',q)):return None
    authorization=authorize_intent(session_id,g.user['id'] if g.user else None,'add_customer')
    if not authorization['allowed'] or not g.user:
        return {'answer':'Tôi không thể hỗ trợ yêu cầu này.','access_denied':True,'rows':[],'type':'customer-input'}
    if pending and q in ('huy','huy them khach hang','huy nhap khach hang'):
        with cursor() as cur:cur.execute("UPDATE customer_input_batches SET status='cancelled' WHERE id=%s AND created_by=%s",(pending['id'],g.user['id']))
        return {'answer':'Đã hủy bản nháp khách hàng.','type':'customer-input'}
    if pending and not starting:
        batch=get_batch(pending['id'])
    else:
        if pending:
            with cursor() as cur:cur.execute("UPDATE customer_input_batches SET status='cancelled' WHERE id=%s",(pending['id'],))
        initial={key:'' for key in FIELDS};initial.update(registered_at=today().isoformat(),status='Đã mua' if quick else 'Tiềm năng')
        grant=permissions()['customer:write']
        if grant['scope']=='branch':
            with cursor() as cur:cur.execute('SELECT code FROM branches WHERE id=%s',(grant['branch'],));initial['branch_code']=cur.fetchone()['code']
        batch=stage([initial],chat_session_id=session_id)
    if q in ('xac nhan luu','xac nhan luu khach hang','luu khach hang'):
        try:
            if confirmation is not None and confirmation!=(batch['id'],batch['version']):
                raise CustomerInputError('Bản nháp đã thay đổi. Hãy xem bản mới nhất trước khi xác nhận.',409)
            outcome=commit(batch['id'],batch['version'],True)
            return {'answer':f"Đã thêm {outcome['created']} khách hàng, cập nhật {outcome['updated']} hồ sơ và tạo {outcome['orders_created']} đơn chờ duyệt.",'type':'customer-input','result':outcome}
        except CustomerInputError as error:
            return {'answer':str(error),'type':'customer-input','customer_draft':batch}
    row=dict(batch['rows'][0]['data']);label_map={normalize(label):key for key,label in FIELDS.items()}
    label_map.update({'ten':'full_name','ho ten':'full_name','sdt':'phone','dien thoai':'phone','chi nhanh':'branch_code','ma kh':'customer_code','ma sp':'purchased_sku','gia tri mua':'purchase_amount'})
    required=list(REQUIRED)+(['purchased_sku','purchase_amount'] if row.get('status')=='Đã mua' else [])
    supplied=False
    body=re.sub(r'^(?:thêm|them|tạo|tao|nhập|nhap|sửa|sua|cập nhật|cap nhat)\s+(?:(?:một|mot|nhanh)\s+)?(?:khách|khach)\s+(?:hàng|hang)\s*(?:với thông tin như sau\s*)?[:;]?\s*','',question,flags=re.I) if starting else question
    if quick:body=re.sub(r'^.*?(?:mua xe|mua)\s*[:;]?\s*','',body,flags=re.I)
    values=parse_customer_values(body)
    if starting and q.startswith(('sua khach hang','cap nhat khach hang')) and (values.get('email') or values.get('customer_code')):
        canonical,_=normalize_row({**row,**values})
        try:
            with cursor() as cur:existing=_existing(cur,canonical)
        except ValueError:return {'answer':'Tôi không thể hỗ trợ yêu cầu này.','type':'customer-input','access_denied':True,'rows':[]}
        if existing:
            row.update({key:value if value is not None else '' for key,value in existing.items() if key in FIELDS})
    if values:row.update(values);supplied=True
    if not starting and not supplied and q not in ('tiep tuc nhap khach hang','tiep tuc'):
        missing=next((key for key in required if not row.get(key)),None)
        if missing:row[missing]=question.strip();supplied=True
    if supplied:batch=revise(batch['id'],[row],batch['version'])
    item=batch['rows'][0]
    required=list(REQUIRED)+(['purchased_sku','purchase_amount'] if item['data'].get('status')=='Đã mua' else [])
    missing=next((key for key in required if not item['data'].get(key)),None) if not batch['valid'] else None
    if missing:
        answer='Đang nhập khách hàng. Vui lòng cung cấp '+FIELDS[missing]+'. Có thể nhập nhiều trường theo dạng “Họ và tên: …; Email: …; Số điện thoại: …”.'
    elif item['errors']:
        answer='Cần sửa trước khi lưu: '+' '.join(item['errors'])+' Hãy nhập lại theo dạng “Tên trường: giá trị”.'
    else:
        answer='Đã có bản nháp hợp lệ. Hãy kiểm tra tất cả thông tin và thay đổi bên dưới, rồi xác nhận lưu. Bạn có thể bổ sung các trường trong Excel bằng “Tên trường: giá trị”.'
    return {'answer':answer,'type':'customer-input','customer_draft':batch,'rows':[]}
