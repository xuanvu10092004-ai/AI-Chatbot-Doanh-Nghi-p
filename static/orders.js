// Lọc, phân trang đơn hàng và chỉ hiện link chứng từ khi có quyền xuất.
'use strict';
(() => {
 const el=id=>document.getElementById(id),node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;};
 // Ánh xạ trạng thái trong DB sang nhãn tiếng Việt.
 const statuses={pending:'Chờ duyệt',approved:'Đã duyệt',paid:'Đã thanh toán',delivered:'Đã giao xe',cancelled:'Đã hủy'};
 let page=1,loading=false;
 async function load(){if(loading)return;loading=true;try{const params=new URLSearchParams({page,q:el('orderSearch').value,status:el('orderStatus').value});const response=await fetch('/api/orders?'+params);const data=await response.json();if(!response.ok)throw new Error(data.message||'Chưa tải được đơn hàng.');const table=node('table'),head=node('thead'),hr=node('tr'),body=node('tbody');['Mã đơn','Khách hàng','Chi nhánh','Ngày lập','Trạng thái','Giá trị','Chứng từ'].forEach(t=>hr.append(node('th',t)));head.append(hr);for(const row of data.rows){const tr=node('tr');[row.id,row.full_name,row.branch_code,new Date(row.created_at).toLocaleDateString('vi-VN'),statuses[row.status],row.amount===null?'Thiếu mặt hàng':new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(row.amount)].forEach(v=>tr.append(node('td',v)));const td=node('td');if(el('orderList').dataset.canExport==='true'&&row.status!=='cancelled'){const link=node('a',['paid','delivered'].includes(row.status)?'Xuất hóa đơn PDF':'Xuất phiếu đơn PDF');link.href='/api/orders/'+row.id+'/invoice.pdf';td.append(link);}else td.textContent='Không khả dụng';tr.append(td);body.append(tr);}table.append(head,body);el('orderList').replaceChildren(table);el('orderFeedback').textContent=data.total+' đơn · Trang '+page;el('orderPrevious').disabled=page<=1;el('orderNext').disabled=page*data.size>=data.total;}catch(e){el('orderFeedback').textContent=e.message;}finally{loading=false;}}
 el('orderFilters').addEventListener('submit',e=>{e.preventDefault();page=1;load();});
 el('orderPrevious').addEventListener('click',()=>{if(!loading){page--;load();}});el('orderNext').addEventListener('click',()=>{if(!loading){page++;load();}});load();
})();
