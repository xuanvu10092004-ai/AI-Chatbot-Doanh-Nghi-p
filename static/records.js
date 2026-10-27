// Tải danh sách khách/tồn kho theo bộ lọc, hiển thị thống kê và lịch sử nhập file.
'use strict';

let page = 1;
let total = 0;
const form = document.getElementById('recordFilters');
const tableBox = document.getElementById('recordTable');
const retryButton = document.getElementById('retryRecords');
const labels = {
  customer_id: 'ID', customer_code: 'Mã khách', full_name: 'Họ tên', email: 'Email',
  phone: 'Điện thoại', branch_code: 'Chi nhánh',
  province: 'Tỉnh/thành', lead_source: 'Nguồn', registered_at: 'Ngày đăng ký',
  model_name: 'Mẫu xe', variant_name: 'Phiên bản', quantity: 'Số xe',
  list_price: 'Giá niêm yết', updated_at: 'Cập nhật', stock_status: 'Trạng thái tồn kho'
};

function renderSummary(summary) {
  const target = document.getElementById('recordSummary');
  target.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = form.dataset.dataset === 'customers'
    ? `Tổng số khách hàng: ${new Intl.NumberFormat('vi-VN').format(summary.total)}`
    : `Tổng tồn kho: ${new Intl.NumberFormat('vi-VN').format(Number(summary.total_stock))} xe · ${summary.variants} phiên bản · ${summary.branches} chi nhánh`;
  target.append(title);
  const hint = document.createElement('p');
  hint.className = 'muted';
  hint.textContent = 'Thống kê toàn bộ kết quả theo bộ lọc và phạm vi quyền, không chỉ trang hiện tại.';
  target.append(hint);
  const maximum = Math.max(1, ...summary.distribution.map(row => Number(row.value)));
  for (const item of summary.distribution) {
    const line = document.createElement('div'); line.className = 'distribution-row';
    const label = document.createElement('span'); label.textContent = item.label || 'Chưa xác định';
    const meter = document.createElement('meter'); meter.min = 0; meter.max = maximum; meter.value = Number(item.value); meter.setAttribute('aria-label', label.textContent);
    const value = document.createElement('strong'); value.textContent = new Intl.NumberFormat('vi-VN').format(Number(item.value));
    line.append(label, meter, value); target.append(line);
  }
}

function displayValue(key, value, cell) {
  if (key === 'list_price') return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(value));
  if (key.endsWith('_at') && value) return new Date(value).toLocaleDateString('vi-VN');
  if (key === 'stock_status') {
    cell.style.fontWeight = 'bold';
    if (value === 'Hết hàng') cell.style.color = '#c0392b';
    if (value === 'Sắp hết hàng') cell.style.color = '#e67e22';
  }
  return String(value ?? '-');
}

function renderRows(rows) {
  if (!rows.length) { tableBox.textContent = 'Chưa có kết quả trong phạm vi của bạn.'; return; }
  const table = document.createElement('table'), thead = document.createElement('thead'), head = document.createElement('tr'), body = document.createElement('tbody');
  const keys = Object.keys(rows[0]).filter(key=>!['version','deleted_at'].includes(key));
  for (const key of keys) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = labels[key] || key; head.append(th); }
  const admin=form.dataset.dataset==='customers'&&form.dataset.customerAdmin==='true';
  if(admin){const th=document.createElement('th');th.scope='col';th.textContent='Thao tác';head.append(th);}
  thead.append(head);
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const key of keys) { const td = document.createElement('td'); td.textContent = displayValue(key, row[key], td); tr.append(td); }
    if(admin){const td=document.createElement('td');td.className='actions';
      const button=(title,handler)=>{const node=document.createElement('button');node.type='button';node.className='secondary';node.textContent=title;node.onclick=handler;td.append(node);};
      if(row.deleted_at)button('Khôi phục',()=>changeCustomerStatus(row,'restore'));
      else{button('Sửa',()=>editCustomer(row.customer_id));button('Xóa',()=>changeCustomerStatus(row,'delete'));}tr.append(td);}
    body.append(tr);
  }
  table.append(thead, body); tableBox.replaceChildren(table);
}

async function load() {
  // Giữ bộ lọc hiện tại và thêm batch nhập nếu trang được mở từ lịch sử khách.
  tableBox.textContent = 'Đang tải…'; retryButton.disabled = true;
  const params = new URLSearchParams(new FormData(form)); params.set('page', page);
  if(document.getElementById('deletedCustomers')?.checked)params.set('deleted','1');
  const imported = new URLSearchParams(location.search).get('import_batch'); if (imported) params.set('import_batch', imported);
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`/api/${form.dataset.dataset}?${params}`, { signal: controller.signal });
    if (!response.ok) throw new Error(`API trả về mã ${response.status}.`);
    const data = await response.json(); total = data.total; renderSummary(data.summary); renderRows(data.rows);
    document.getElementById('pageInfo').textContent = `Trang ${page} · ${total} kết quả`;
    document.getElementById('previousPage').disabled = page <= 1; document.getElementById('nextPage').disabled = page * data.size >= total;
  } catch (error) {
    tableBox.textContent = error.name === 'AbortError' ? 'Tải dữ liệu quá lâu. Hãy thử lại.' : 'Không tải được dữ liệu. Hãy thử lại.';
  } finally { clearTimeout(timeout); retryButton.disabled = false; }
}

let editingCustomer=null;
async function customerApi(url,method='GET',data){
  const response=await fetch(url,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},...(data?{body:JSON.stringify(data)}:{})});
  const result=await response.json();if(!response.ok)throw new Error(result.message||'Chưa xử lý được yêu cầu.');return result;
}
async function editCustomer(id){
  const message=document.getElementById('customerAdminMessage');
  try{
    const [detail,lookup]=await Promise.all([customerApi('/api/customers/'+id),customerApi('/api/customer-input/lookups')]);
    editingCustomer=detail.customer;const box=document.getElementById('customerEditFields');box.replaceChildren();
    for(const [key,title] of Object.entries(lookup.fields).filter(([k])=>!['purchased_sku','purchase_amount'].includes(k))){
      const label=document.createElement('label');label.textContent=title;
      const options={branch_code:lookup.branches.map(r=>r.code),interested_model:lookup.models,status:['Tiềm năng','Đang tư vấn','Đã mua','Ngừng liên hệ'],gender:['Nam','Nữ'],payment_preference:['Trả thẳng','Trả góp']}[key];
      const input=document.createElement(options?'select':'input');input.name=key;input.id='editCustomer_'+key;
      if(options){for(const value of ['',...options]){const option=document.createElement('option');option.value=value;option.textContent=value||'Chưa cung cấp';input.append(option);}}
      else input.type=key==='email'?'email':key.endsWith('_date')||key==='registered_at'?'date':'text';
      let value=editingCustomer[key]??'';if(input.type==='date'&&value)value=new Date(value).toISOString().slice(0,10);input.value=value;
      if(lookup.required.includes(key))input.required=true;label.append(input);box.append(label);
    }
    document.getElementById('customerEditError').textContent='';document.getElementById('customerEditor').showModal();
  }catch(error){message.textContent=error.message;}
}
async function changeCustomerStatus(row,operation){
  const title=operation==='delete'?'Xóa mềm':'Khôi phục';
  if(!confirm(title+' khách '+row.full_name+'? Đơn hàng và lịch sử vẫn được giữ nguyên.'))return;
  const message=document.getElementById('customerAdminMessage');
  try{await customerApi('/api/customers/'+row.customer_id+(operation==='restore'?'/restore':''),operation==='restore'?'POST':'DELETE',{version:row.version,confirmed:true});message.textContent='Đã '+title.toLowerCase()+' khách hàng. Excel chờ worker đồng bộ.';await load();await refreshExcelStatus();}catch(error){message.textContent=error.message;}
}
async function refreshExcelStatus(){
  const node=document.getElementById('excelSyncStatus');if(!node)return;
  try{const state=await customerApi('/api/excel-sync');const labels={completed:'Đã đồng bộ',pending:'Đang chờ worker',running:'Đang xuất Excel',failed:'Đồng bộ lỗi, sẽ thử lại'};node.textContent='Excel: '+(labels[state.status]||'Chưa xác định')+' · '+state.pending+' thay đổi chờ xử lý'+(state.last_success_at?' · Thành công gần nhất: '+new Date(state.last_success_at).toLocaleString('vi-VN'):' · Chưa có lần đồng bộ thành công')+(state.error?' · '+state.error:'');}catch(error){node.textContent='Chưa đọc được trạng thái đồng bộ Excel.';}
}
document.getElementById('deletedCustomers')?.addEventListener('change',()=>{page=1;load();});
document.getElementById('cancelCustomerEdit')?.addEventListener('click',()=>document.getElementById('customerEditor').close());
document.getElementById('customerEditForm')?.addEventListener('submit',async event=>{
  event.preventDefault();const button=document.getElementById('saveCustomerEdit');button.disabled=true;
  try{const data={version:editingCustomer.version};for(const [key,value] of new FormData(event.target)){let before=editingCustomer[key]??'';if((key.endsWith('_date')||key==='registered_at')&&before)before=new Date(before).toISOString().slice(0,10);if(String(before)!==value)data[key]=value;}
    if(Object.keys(data).length===1){document.getElementById('customerEditError').textContent='Chưa có thông tin thay đổi.';return;}
    await customerApi('/api/customers/'+editingCustomer.id,'PATCH',data);document.getElementById('customerEditor').close();document.getElementById('customerAdminMessage').textContent='Đã lưu hồ sơ. Excel chờ worker đồng bộ.';await load();await refreshExcelStatus();
  }catch(error){document.getElementById('customerEditError').textContent=error.message;}finally{button.disabled=false;}
});
if(document.getElementById('excelSyncStatus')){refreshExcelStatus();setInterval(refreshExcelStatus,5000);}

form.addEventListener('submit', event => { event.preventDefault(); page = 1; load(); });
document.getElementById('previousPage').addEventListener('click', () => { if (page > 1) { page--; load(); } });
document.getElementById('nextPage').addEventListener('click', () => { page++; load(); });
retryButton.addEventListener('click', load); load();

if (document.getElementById('customerImportHistory')) {
  fetch('/api/customer-imports').then(response => { if (!response.ok) throw new Error(); return response.json(); }).then(data => {
    const box = document.getElementById('customerImportHistory'); box.replaceChildren();
    if (!data.rows.length) { box.textContent = 'Chưa có danh sách được xác nhận nhập từ file trong phạm vi của bạn.'; return; }
    const table = document.createElement('table'), head = document.createElement('tr');
    ['File', 'Định dạng', 'Số khách trong phạm vi', 'Thêm mới', 'Cập nhật', 'Ngày nhập', 'Danh sách'].forEach(value => { const th = document.createElement('th'); th.textContent = value; head.append(th); }); table.append(head);
    for (const row of data.rows) {
      const tr = document.createElement('tr');
      [row.original_name, row.file_format.toUpperCase(), row.customer_count, row.created, row.updated, new Date(row.updated_at).toLocaleString('vi-VN')].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
      const td = document.createElement('td'), link = document.createElement('a'); link.textContent = 'Xem khách đã cập nhật'; link.href = `/customers?import_batch=${row.id}`; td.append(link); tr.append(td); table.append(tr);
    }
    box.append(table);
  }).catch(() => { document.getElementById('customerImportHistory').textContent = 'Chưa tải được lịch sử. Hãy tải lại trang.'; });
}
