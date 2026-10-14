'use strict';
(() => {
  const el = id => document.getElementById(id);
  const feedback = el('documentFeedback');
  const statuses = {uploaded:'Đã tải lên',processing:'Đang trích xuất',ready:'Có nội dung',needs_review:'Cần kiểm tra / bổ sung',failed:'Trích xuất lỗi',published:'Đã vào kho tri thức'};
  let selected=null, page=1, total=0, busy=false;
  const tell = (message,error=false) => {feedback.textContent=message;feedback.className=error?'error':'';el('previewFeedback').textContent=el('documentPreview').hidden?'':message;el('previewFeedback').className=error?'error':'';};
  async function api(url,options={}) {
    const response=await fetch(url,{...options,headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content,...options.headers}});
    const data=await response.json();
    if(!response.ok)throw new Error(data.message||'Không thực hiện được yêu cầu. Hãy tải lại trang.');
    return data;
  }
  const json = data => ({headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const node = (tag,text) => {const item=document.createElement(tag);if(text!==undefined)item.textContent=String(text);return item;};
  async function refresh() {
    const data=await api('/api/documents?page='+page);total=data.total;
    const table=node('table'),head=node('thead'),tr=node('tr'),body=node('tbody');
    ['Tiêu đề','File','Danh mục / chi nhánh','Trạng thái','Ngày tải','Thao tác'].forEach(label=>{const th=node('th',label);th.scope='col';tr.append(th);});head.append(tr);
    for(const row of data.rows){const line=node('tr');
      [row.title,row.original_name,row.category_name+' / '+(row.branch_code||'Toàn hệ thống'),row.category_code==='customers'&&row.customer_synced?'Đã đồng bộ khách hàng':statuses[row.status],new Date(row.created_at).toLocaleDateString('vi-VN')].forEach(value=>line.append(node('td',value)));
      const cell=node('td'),button=node('button','Xem và kiểm tra');button.type='button';button.className='secondary';button.addEventListener('click',()=>open(row.id).catch(error=>tell(error.message,true)));cell.append(button);line.append(cell);body.append(line);
    }
    table.append(head,body);el('documentList').replaceChildren(data.rows.length?table:node('p','Chưa có tài liệu trong phạm vi bạn được xem.'));
    el('documentPagination').textContent='Trang '+page+' · '+total+' tài liệu';el('documentPrevious').disabled=page===1;el('documentNext').disabled=page*25>=total;
  }
  function render(data) {
    selected=data;el('documentPreview').hidden=false;el('previewTitle').textContent='Xem trước: '+data.title;
    el('documentMetadata').textContent=statuses[data.status]+' · '+(data.size_bytes/1024).toFixed(1)+' KB · '+data.file_format.toUpperCase()+' · '+(data.branch_code||'Toàn hệ thống');
    el('downloadDocument').href='/api/documents/'+data.id+'/file';
    el('customerImportLink').hidden=data.category_code!=='customers';el('customerImportLink').href='/customer-input?document_id='+data.id;
    el('documentReview').hidden=data.category_code==='customers';
    const warnings=el('extractionWarnings');warnings.replaceChildren();
    if(data.error_message)warnings.append(node('p',data.error_message));
    const extracted=data.extraction;
    if(extracted){warnings.append(node('p',extracted.quality.confidence_note));
      if(extracted.metadata.text_page_coverage!==undefined)warnings.append(node('p','Trang có lớp văn bản: '+Math.round(extracted.metadata.text_page_coverage*100)+'% (không phải độ chính xác OCR).'));
      for(const warning of extracted.quality.warnings)warnings.append(node('p',warning));
    }
    const blocks=el('extractionBlocks');blocks.replaceChildren();
    if(!extracted?.blocks?.length)blocks.append(node('p','Chưa có nội dung trích xuất. Có thể nhập bản đã đối chiếu ở phần dưới.'));
    for(const block of extracted?.blocks||[]){const section=node('section');section.className='extraction-block';
      const loc=block.location;section.append(node('h3',loc.sheet?'Sheet '+loc.sheet:loc.page?'Trang '+loc.page+(loc.column?' · Cột '+loc.column:''):'Khối '+(loc.block||loc.section)));
      if(block.kind==='text'){const text=node('pre',block.text);text.className='extracted-text';section.append(text);}
      else {const table=node('table'),body=node('tbody');for(const row of block.rows){const tr=node('tr');for(const cell of row)tr.append(node('td',cell||'[Trống]'));body.append(tr);}table.append(body);const wrap=node('div');wrap.className='table-scroll';wrap.tabIndex=0;wrap.append(table);section.append(wrap);}
      blocks.append(section);
    }
    el('reviewTitle').value=data.title;el('reviewContent').value=data.review_content??extracted?.text??'';el('reviewNotes').value=data.review_notes||'';el('reviewConfirmed').checked=false;
    const editable=['ready','needs_review'].includes(data.status);
    ['reviewTitle','reviewContent','reviewNotes','reviewConfirmed','saveDocumentReview'].forEach(id=>el(id).disabled=!editable);
    el('publishDocument').disabled=data.category_code==='customers'||!data.reviewed_at||data.status!=='ready';el('retryDocument').hidden=!['failed','uploaded','processing'].includes(data.status);
    el('reviewNotes').required=data.status==='needs_review';
  }
  async function open(id){render(await api('/api/documents/'+id));el('documentPreview').scrollIntoView({block:'start',behavior:'smooth'});}
  async function action(fn){if(busy)return;busy=true;try{await fn();}catch(error){tell(error.message,true);}finally{busy=false;}}
  el('documentUpload').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const file=el('documentFile').files[0];if(!file)throw new Error('Vui lòng chọn file.');
    if(!/\.(pdf|docx|xlsx)$/i.test(file.name))throw new Error('Chỉ nhận PDF, DOCX hoặc XLSX.');
    if(file.size===0||file.size>10*1024*1024)throw new Error('File không được rỗng hoặc vượt quá 10 MB.');
    el('uploadDocumentButton').disabled=true;tell('Đang tải lên và trích xuất; tài liệu chưa được đưa vào kho tri thức.');
    try{const data=await api('/api/documents',{method:'POST',body:new FormData(event.target)});render(data);page=1;await refresh();tell(data.status==='failed'?data.error_message:'Đã trích xuất. Hãy đối chiếu nội dung và các cảnh báo.',data.status==='failed');}
    finally{el('uploadDocumentButton').disabled=false;}
  });});
  el('documentReview').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const data=await api('/api/documents/'+selected.id+'/review',{method:'PUT',...json({title:el('reviewTitle').value,content:el('reviewContent').value,notes:el('reviewNotes').value,confirmed:el('reviewConfirmed').checked,version:selected.version})});render(data);await refresh();tell('Đã lưu bản kiểm tra. Chưa đưa vào kho tri thức.');
  });});
  el('publishDocument').addEventListener('click',()=>action(async()=>{const data=await api('/api/documents/'+selected.id+'/publish',{method:'POST',...json({version:selected.version})});render(data);await refresh();tell('Đã đưa bản đã kiểm tra vào kho tri thức. Nguồn tài liệu #'+data.published_doc_id+'.');}));
  // Sửa tiếp nội dung phải lưu và xác nhận lại trước khi xuất bản.
  ['reviewTitle','reviewContent','reviewNotes'].forEach(id=>el(id).addEventListener('input',()=>{el('publishDocument').disabled=true;el('reviewConfirmed').checked=false;}));
  el('retryDocument').addEventListener('click',()=>action(async()=>{tell('Đang trích xuất lại…');render(await api('/api/documents/'+selected.id+'/process',{method:'POST'}));await refresh();tell('Đã cập nhật trạng thái trích xuất.');}));
  el('refreshDocuments').addEventListener('click',()=>refresh().catch(error=>tell(error.message,true)));
  el('chooseDocumentFile').addEventListener('click',()=>el('documentFile').click());
  el('documentFile').addEventListener('change',()=>{el('documentFileName').textContent=el('documentFile').files[0]?.name||'Chưa chọn file';});
  el('documentCategory').addEventListener('change',()=>{el('customerTemplateLink').hidden=el('documentCategory').selectedOptions[0]?.dataset.categoryCode!=='customers';});
  el('documentPrevious').addEventListener('click',()=>{page--;refresh().catch(error=>tell(error.message,true));});
  el('documentNext').addEventListener('click',()=>{page++;refresh().catch(error=>tell(error.message,true));});
  api('/api/documents/lookups').then(data=>{for(const category of data.categories){const option=node('option',category.name);option.value=category.id;option.dataset.categoryCode=category.category_code;el('documentCategory').append(option);}if(data.all_branches){const option=node('option','Toàn hệ thống');option.value='';el('documentBranch').append(option);}for(const branch of data.branches){const option=node('option',branch.code+' · '+branch.name);option.value=branch.id;el('documentBranch').append(option);}return refresh();}).catch(error=>tell(error.message,true));
})();
