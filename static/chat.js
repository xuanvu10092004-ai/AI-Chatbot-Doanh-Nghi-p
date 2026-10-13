'use strict';
const form=document.getElementById('chatForm');
form.addEventListener('submit',async event=>{
  event.preventDefault();const input=document.getElementById('questionInput'),button=document.getElementById('sendButton'),messages=document.getElementById('chatMessages');
  const question=input.value.trim();if(!question||button.disabled)return;
  const add=(text,kind)=>{const node=document.createElement('div');node.className='message '+kind;node.textContent=text;messages.append(node);return node;};
  add(question,'user-message');input.value='';button.disabled=true;const bot=add('Đang tra cứu…','bot-message');
  try{
    const response=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({question})});
    const data=await response.json();bot.textContent=data.answer||data.message||'Chưa xử lý được yêu cầu.';
    if(data.rows&&data.rows.length){
      bot.textContent='Kết quả từ dữ liệu Honda mô phỏng';
      const table=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr'),body=document.createElement('tbody');
      const labels={model_name:'Mẫu xe',variant_name:'Phiên bản',list_price:'Giá niêm yết',quantity:'Số xe',total_stock:'Tồn kho',branch_code:'Chi nhánh',color:'Màu',engine_cc:'Dung tích (cc)',segment:'Phân khúc',warranty:'Bảo hành',fuel_tank_l:'Bình xăng (lít)',weight_kg:'Khối lượng (kg)',engine_type:'Động cơ',brake_type:'Phanh',fuel_consumption_l100km:'Lít/100 km',description:'Mô tả',full_name:'Họ tên',customer_status:'Trạng thái',phone:'Điện thoại',email:'Email'};
      const cols=Object.keys(data.rows[0]).filter(k=>!['product_id','variant_id'].includes(k));
      for(const key of cols){const th=document.createElement('th');th.scope='col';th.textContent=labels[key]||key;hr.append(th);}head.append(hr);
      for(const row of data.rows){const tr=document.createElement('tr');for(const key of cols){const td=document.createElement('td');let value=row[key];if(value===null)value='Chưa có dữ liệu';else if(/price|amount|revenue|margin/.test(key)&&!isNaN(Number(value)))value=new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(Number(value));else if(key==='segment')value={tay_ga:'Xe ga',xe_so:'Xe số',con_tay:'Xe côn tay'}[value]||value;td.textContent=String(value);tr.append(td);}body.append(tr);}table.append(head,body);const wrapper=document.createElement('div');wrapper.className='table-scroll';wrapper.append(table);bot.append(wrapper);
    }
    if(data.sources?.length){const source=document.createElement('p');source.className='sources';source.textContent='Nguồn: '+data.sources.map(s=>'#'+s.id+' · '+s.title).join('; ');bot.append(source);}
  }catch(error){bot.textContent='Không kết nối được hệ thống. Vui lòng thử lại.';}
  finally{button.disabled=false;messages.scrollTop=messages.scrollHeight;input.focus();}
});
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{document.getElementById('questionInput').value=button.dataset.question;document.getElementById('questionInput').focus();}));
