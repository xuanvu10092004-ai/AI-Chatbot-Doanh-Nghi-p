// Gửi câu hỏi/file tới backend rồi dựng câu trả lời, nguồn và bản xem trước bằng DOM an toàn.
'use strict';
const form=document.getElementById('chatForm');
form.addEventListener('submit',async event=>{
  event.preventDefault();const input=document.getElementById('questionInput'),button=document.getElementById('sendButton'),messages=document.getElementById('chatMessages');
  const attachment=document.getElementById('chatCustomerFile')?.files[0];const question=input.value.trim()||(attachment?'Nhập danh sách khách từ file '+attachment.name:'');if(!question||button.disabled)return;
  const confirmation=form.customerConfirmation||{};delete form.customerConfirmation;
  const add=(text,kind)=>{const node=document.createElement('div');node.className='message '+kind;node.textContent=text;messages.append(node);return node;};
  add(question,'user-message');input.value='';button.disabled=true;const bot=add('Đang tra cứu…','bot-message');
  messages.scrollTop=messages.scrollHeight;
  bot.setAttribute('aria-busy','true');
  try{
    // File khách gửi multipart; câu hỏi văn bản gửi JSON cùng dữ liệu xác nhận lệnh.
    let response;if(attachment){const upload=new FormData();upload.append('file',attachment);response=await fetch('/api/chat/customer-file',{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:upload});document.getElementById('chatCustomerFile').value='';document.getElementById('chatAttachmentName').textContent='';}else response=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({question,...confirmation})});
    const data=await response.json();
    // Dựng đậm/nghiêng bằng DOM an toàn, không parse HTML của LLM.
    ChatFormatting.render(bot,data.summary||data.answer||data.message||'Chưa xử lý được yêu cầu.');
    if(data.action_draft){
      const draft=data.action_draft,preview=document.createElement('pre');preview.className='extracted-text';
      const names={branch_id:'ID chi nhánh',supplier:'Nhà cung cấp',reference_code:'Chứng từ',items:'Các dòng hàng',id:'Mã bản ghi',full_name:'Họ tên',phone:'SĐT',scheduled_at:'Ngày giờ',kind:'Loại lịch',status:'Trạng thái',list_price:'Giá niêm yết',model_name:'Mẫu xe',variant_name:'Phiên bản',model_year:'Năm đời',roles:'Vai trò',permissions:'Quyền'};
      preview.textContent=Object.entries(draft.arguments).map(([k,v])=>(names[k]||k)+': '+(typeof v==='object'?JSON.stringify(v,null,2):v)).join('\n');bot.append(preview);
      let password;if(draft.requires_password){const label=document.createElement('label');label.textContent='Mật khẩu tạm (ô bảo mật, không lưu vào hội thoại)';password=document.createElement('input');password.type='password';password.minLength=10;password.maxLength=256;password.required=true;password.autocomplete='new-password';label.append(password);bot.append(label);}
      const controls=document.createElement('div');controls.className='actions';const confirm=document.createElement('button');confirm.type='button';confirm.textContent='Xác nhận lệnh #'+draft.id;
      confirm.onclick=()=>{if(password&&!password.reportValidity())return;input.value='Xác nhận lệnh '+draft.id;form.customerConfirmation={action_id:draft.id,action_version:draft.version,...(password?{action_secret:password.value}:{})};if(password)password.value='';form.requestSubmit();confirm.disabled=true;};
      const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='Hủy lệnh';cancel.onclick=()=>{input.value='Hủy lệnh '+draft.id;form.requestSubmit();confirm.disabled=true;cancel.disabled=true;};controls.append(confirm,cancel);bot.append(controls);
    }
    if(data.download_url){const download=document.createElement('a');download.href=data.download_url;download.textContent='Tải chứng từ PDF';bot.append(download);}
    if(data.customer_draft){
      const draft=data.customer_draft, row=draft.rows[0];
      const details=document.createElement('p');details.textContent='Bản nháp khách hàng #'+draft.id+' · '+(row.action==='update'?'Cập nhật hồ sơ':'Thêm mới')+' · '+(draft.valid?'Đủ trường bắt buộc':'Cần bổ sung / sửa thông tin');bot.append(details);
      const draftActions=document.createElement('div');draftActions.className='actions';const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='Hủy bản nháp';cancel.addEventListener('click',()=>{input.value='Hủy nhập khách hàng';form.requestSubmit();cancel.disabled=true;});draftActions.append(cancel);bot.append(draftActions);for(const error of row.errors||[]){const hint=document.createElement('p');hint.className='field-help';hint.textContent=error;bot.append(hint);}const link=document.createElement('a');link.href='/customer-input?batch='+draft.id;link.textContent='Xem và chỉnh đầy đủ thông tin theo Excel';bot.append(link);
      for(const warning of draft.warnings||[]){const note=document.createElement('p');note.className='field-help';note.textContent=warning;bot.append(note);}
      if(draft.rows.length>1){const all=document.createElement('details'),title=document.createElement('summary');title.textContent='Kiểm tra toàn bộ '+draft.rows.length+' dòng khách hàng';all.append(title);for(const item of draft.rows){const pre=document.createElement('pre');pre.className='extracted-text';pre.textContent='Dòng '+item.row+' · '+(item.action==='update'?'Cập nhật':'Thêm mới')+'\n'+Object.entries(item.data).filter(([k,v])=>v!==null&&v!=='').map(([k,v])=>(draft.fields[k]||k)+': '+v).join('\n')+'\n'+item.errors.join('\n');all.append(pre);}bot.append(all);}
      if(draft.valid){
        const preview=document.createElement('pre');preview.className='extracted-text';
        preview.textContent=Object.entries(row.data).filter(([k,v])=>v!==null&&v!=='').map(([k,v])=>(draft.fields[k]||k)+': '+(['birth_date','registered_at'].includes(k)?new Date(v+'T00:00:00').toLocaleDateString('vi-VN'):k==='purchase_amount'?new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(v):v)).join('\n');
        if(row.age!==undefined)preview.textContent+='\nTuổi: '+row.age;
        for(const [key,change] of Object.entries(row.changes))preview.textContent+='\nThay đổi '+(draft.fields[key]||key)+': '+(change.before||'(trống)')+' → '+(change.after||'(trống)');
        if(row.order_action)preview.textContent+='\n'+(row.order_action==='existing'?'Đã nhận diện đơn hiện có.':'Sẽ tạo đơn chờ duyệt, số lượng 1: '+row.variant_name);
        bot.append(preview);
        const confirm=document.createElement('button');confirm.type='button';confirm.textContent='Xác nhận lưu khách hàng';
        confirm.addEventListener('click',()=>{input.value='Xác nhận lưu khách hàng';form.customerConfirmation={customer_batch_id:draft.id,customer_batch_version:draft.version};form.requestSubmit();confirm.disabled=true;});bot.append(confirm);
      }
    }
    if(data.result?.document_id&&data.result?.batch_id){const link=document.createElement('a');link.href='/customers?import_batch='+data.result.batch_id;link.textContent='Xem danh sách khách hàng vừa đồng bộ';bot.append(link);}
    if(data.result?.order_ids&&form.dataset.canExport==='true'){for(const id of data.result.order_ids){const p=document.createElement('p'),link=document.createElement('a');link.href='/api/orders/'+id+'/invoice.pdf';link.textContent='Xuất phiếu đơn #'+id+' (PDF mô phỏng)';p.append(link);bot.append(p);}}
    if(data.rows&&data.rows.length){
      const table=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr'),body=document.createElement('tbody');
      const labels={model_year:'Năm đời xe',lifecycle:'Kinh doanh',model_name:'Mẫu xe',variant_name:'Phiên bản',list_price:'Giá niêm yết',quantity:'Số xe',total_stock:'Tồn kho',branch_code:'Mã chi nhánh',branch_name:'Tên chi nhánh',color:'Màu',engine_cc:'Dung tích (cc)',segment:'Phân khúc',warranty:'Bảo hành',fuel_tank_l:'Bình xăng (lít)',weight_kg:'Khối lượng (kg)',engine_type:'Động cơ',brake_type:'Phanh',fuel_consumption_l100km:'Lít/100 km',description:'Mô tả',full_name:'Họ tên',customer_status:'Trạng thái',phone:'Điện thoại',email:'Email'};
      const keys=Object.keys(data.rows[0]).filter(k=>!['product_id','variant_id'].includes(k));
      const priority=['model_name','variant_name','branch_code','branch_name','quantity','total_stock','list_price','engine_cc','color','segment'];
      const cols=[...priority.filter(k=>keys.includes(k)),...keys.filter(k=>!priority.includes(k))];
      for(const key of cols){const th=document.createElement('th');th.scope='col';th.textContent=labels[key]||key;hr.append(th);}head.append(hr);
      for(const row of data.rows){const tr=document.createElement('tr');for(const key of cols){const td=document.createElement('td');let value=row[key];if(value===null)value='Chưa có dữ liệu';else if(/price|amount|revenue|margin/.test(key)&&!isNaN(Number(value)))value=new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(Number(value));else if(key==='lifecycle')value={current:'Đời hiện hành',previous:'Đời trước',discontinued:'Ngừng kinh doanh'}[value]||value;else if(key==='segment')value={tay_ga:'Xe ga',xe_so:'Xe số',con_tay:'Xe côn tay'}[value]||value;td.textContent=ChatFormatting.normalize(value);tr.append(td);}body.append(tr);}table.append(head,body);const wrapper=document.createElement('div');wrapper.className='table-scroll';wrapper.tabIndex=0;wrapper.setAttribute('role','region');wrapper.setAttribute('aria-label','Bảng kết quả tra cứu, cuộn ngang để xem đầy đủ các cột');wrapper.append(table);bot.append(wrapper);
      const hint=document.createElement('p');hint.className='table-hint';hint.textContent='Cuộn ngang bảng để xem các cột còn lại.';bot.append(hint);
    }
    if(data.sources?.length){const source=document.createElement('p');source.className='sources';source.textContent='Nguồn: '+data.sources.map(s=>'#'+s.id+' · '+ChatFormatting.normalize(s.title)).join('; ');bot.append(source);}
  }catch(error){bot.textContent='Không kết nối được hệ thống. Vui lòng thử lại.';}
  finally{bot.removeAttribute('aria-busy');button.disabled=false;messages.scrollTop=bot.offsetTop;input.focus({preventScroll:true});}
});
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{document.getElementById('questionInput').value=button.dataset.question;document.getElementById('questionInput').focus();}));
document.getElementById('chatCustomerFile')?.addEventListener('change',event=>{const file=event.target.files[0];document.getElementById('chatAttachmentName').textContent=file?'Đã chọn '+file.name+' — bấm Gửi để đọc và xem trước.':'';if(file)document.getElementById('questionInput').value='Nhập danh sách khách từ file '+file.name;});
fetch('/api/chat/tools').then(r=>r.json()).then(data=>{const target=document.getElementById('chatToolCatalog');target.replaceChildren();for(const tool of data.tools||[]){const line=document.createElement('p');line.textContent=tool.description+(tool.requires_confirmation?' · Cần xác nhận':'');target.append(line);}}).catch(()=>{document.getElementById('chatToolCatalog').textContent='Nhập “Trợ giúp” để xem công cụ theo quyền hiện tại.';});
