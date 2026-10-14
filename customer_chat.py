"""Thu thập khách hàng qua hội thoại; chỉ gọi công cụ ghi được backend kiểm tra."""
import json
import re
from flask import g
from db import cursor
from security import permissions
from question_language import normalize
from customer_input import FIELDS,REQUIRED,today,stage,get_batch,revise,commit,CustomerInputError
from access_control import authorize_intent


def handle_customer_chat(question,session_id,confirmation=None):
    q=normalize(question)
    quick=bool(re.match(r'^(?:them|tao|nhap) (?:nhanh )?khach (?:hang )?(?:mua xe|da dong y mua)\b',q))
    starting=quick or bool(re.match(r'^(?:them|tao|nhap) (?:mot )?khach hang\b',q))
    with cursor() as cur:
        cur.execute("SELECT id FROM customer_input_batches WHERE chat_session_id=%s AND created_by=%s AND status='draft' ORDER BY id DESC LIMIT 1",(session_id,g.user['id'] if g.user else None))
        pending=cur.fetchone()
    if not starting and not pending:return None
    authorization=authorize_intent(session_id,g.user['id'] if g.user else None,'add_customer')
    if not authorization['allowed'] or not g.user:
        return {'answer':'Tôi không thể hỗ trợ yêu cầu này.','access_denied':True,'rows':[],'type':'customer-input'}
    if pending and q in ('huy','huy them khach hang','huy nhap khach hang'):
        with cursor() as cur:cur.execute("UPDATE customer_input_batches SET status='cancelled' WHERE id=%s AND created_by=%s",(pending['id'],g.user['id']))
        return {'answer':'Đã hủy bản nháp khách hàng.','type':'customer-input'}
    if not starting and not q.startswith('gia tri mua:') and re.match(r'^(gia |ton kho|so sanh|thong so|khuyen mai|tong |danh sach)',q):return None
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
    body=re.sub(r'^(?:thêm|them|tạo|tao|nhập|nhap)\s+(?:(?:một|mot)\s+)?(?:khách|khach)\s+(?:hàng|hang)\s*[:;]?\s*','',question,flags=re.I) if starting else question
    if quick:body=re.sub(r'^.*?(?:mua xe|mua)\s*[:;]?\s*','',body,flags=re.I)
    for part in re.split(r'[;\n]',body):
        if ':' in part:
            label,value=part.split(':',1);label=normalize(label)
            label=re.sub(r'^(them|tao|nhap) khach hang\s*','',label)
            key=label_map.get(label)
            if key:row[key]=value.strip();supplied=True
    if not starting and not supplied:
        missing=next((key for key in required if not row.get(key)),None)
        if missing:row[missing]=question.strip();supplied=True
    if supplied:batch=revise(batch['id'],[row],batch['version'])
    item=batch['rows'][0]
    required=list(REQUIRED)+(['purchased_sku','purchase_amount'] if item['data'].get('status')=='Đã mua' else [])
    missing=next((key for key in required if not item['data'].get(key)),None)
    if missing:
        answer='Đang nhập khách hàng. Vui lòng cung cấp '+FIELDS[missing]+'. Có thể nhập nhiều trường theo dạng “Họ và tên: …; Email: …; Số điện thoại: …”.'
    elif item['errors']:
        answer='Cần sửa trước khi lưu: '+' '.join(item['errors'])+' Hãy nhập lại theo dạng “Tên trường: giá trị”.'
    else:
        answer='Đã có bản nháp hợp lệ. Hãy kiểm tra tất cả thông tin và thay đổi bên dưới, rồi xác nhận lưu. Bạn có thể bổ sung các trường trong Excel bằng “Tên trường: giá trị”.'
    return {'answer':answer,'type':'customer-input','customer_draft':batch,'rows':[]}
