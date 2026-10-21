// Quản lý upload, duyệt trích xuất, xuất bản tài liệu và nhập danh sách khách.
'use strict';
(() => {
  const el = id => document.getElementById(id);
  const feedback = el('documentFeedback');
  // Chuyển mã trạng thái backend thành nhãn tiếng Việt hiển thị trong danh sách.
  const statuses = {uploaded:'Đã tải lên',processing:'Đang trích xuất',ready:'Có nội dung',needs_review:'Cần kiểm tra / bổ sung',failed:'Trích xuất lỗi',published:'Đã vào kho tri thức'};
  // Lưu tài liệu đang xem, vị trí phân trang và trạng thái các thao tác bất đồng bộ.
  let selected=null, page=1, total=0, busy=false, importBatch=null, canImport=false;
  // Hiển thị lỗi ở danh sách và ở khung xem trước nếu khung đó đang mở.
  const tell = (message,error=false) => {feedback.textContent=message;feedback.className=error?'error':'';el('previewFeedback').textContent=el('documentPreview').hidden?'':message;el('previewFeedback').className=error?'error':'';};
  async function api(url,options={}) {
    // Gắn CSRF token vào mọi lời gọi API; phần backend vẫn xác thực quyền truy cập.
    const response=await fetch(url,{...options,headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content,...options.headers}});
    const data=await response.json();
    // Chuyển lỗi HTTP thành thông báo để các trình xử lý sự kiện hiển thị.
    if(!response.ok)throw new Error(data.message||'Không thực hiện được yêu cầu. Hãy tải lại trang.');
    return data;
  }
  // Đóng gói body JSON và Content-Type cho các API nhận dữ liệu JSON.
  const json = data => ({headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  // Dùng textContent thay vì HTML để nội dung tài liệu không được diễn giải thành markup.
  const node = (tag,text) => {const item=document.createElement(tag);if(text!==undefined)item.textContent=String(text);return item;};
  async function refresh() {
    // Tải trang hiện tại rồi dựng lại bảng bằng các node DOM an toàn.
    const data=await api('/api/documents?page='+page);total=data.total;
    const table=node('table'),head=node('thead'),tr=node('tr'),body=node('tbody');
    ['Tiêu đề','File','Danh mục / chi nhánh','Trạng thái','Ngày tải','Thao tác'].forEach(label=>{const th=node('th',label);th.scope='col';tr.append(th);});head.append(tr);
    for(const row of data.rows){const line=node('tr');
      [row.title,row.original_name,row.category_name+' / '+(row.branch_code||'Toàn hệ thống'),row.category_code==='customers'&&row.customer_synced?'Đã đồng bộ khách hàng':statuses[row.status],new Date(row.created_at).toLocaleDateString('vi-VN')].forEach(value=>line.append(node('td',value)));
      const cell=node('td'),button=node('button','Xem và kiểm tra');button.type='button';button.className='secondary';button.addEventListener('click',()=>open(row.id).catch(error=>tell(error.message,true)));cell.append(button);line.append(cell);body.append(line);
    }
    table.append(head,body);el('documentList').replaceChildren(data.rows.length?table:node('p','Chưa có tài liệu trong phạm vi bạn được xem.'));
    // Khóa nút phân trang khi đang ở trang đầu hoặc đã tải hết kết quả.
    el('documentPagination').textContent='Trang '+page+' · '+total+' tài liệu';el('documentPrevious').disabled=page===1;el('documentNext').disabled=page*25>=total;
  }
  function render(data) {
    // Đồng bộ biểu mẫu xem xét với tài liệu được API trả về.
    selected=data;importBatch=null;el('customerImportPanel').hidden=data.category_code!=='customers'||!canImport;el('customerImportPreview').replaceChildren();el('commitCustomerImport').disabled=true;el('confirmCustomerImport').checked=false;el('customerImportFeedback').textContent=data.customer_synced?'File này đã được đồng bộ; mở danh sách khách hàng để xem.':'';el('documentPreview').hidden=false;el('previewTitle').textContent='Xem trước: '+data.title;
    el('documentMetadata').textContent=statuses[data.status]+' · '+(data.size_bytes/1024).toFixed(1)+' KB · '+data.file_format.toUpperCase()+' · '+(data.branch_code||'Toàn hệ thống');
    el('downloadDocument').href='/api/documents/'+data.id+'/file';
    el('customerImportLink').hidden=data.category_code!=='customers';el('customerImportLink').href='/customer-input?document_id='+data.id;
    el('documentReview').hidden=data.category_code==='customers';
    const warnings=el('extractionWarnings');warnings.replaceChildren();
    if(data.error_message)warnings.append(node('p',data.error_message));
    const extracted=data.extraction;
    // Hiển thị cảnh báo và mức bao phủ văn bản để người dùng tự đối chiếu file gốc.
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
    // Chỉ cho sửa nội dung ở trạng thái đã trích xuất hoặc cần người dùng kiểm tra.
    const editable=['ready','needs_review'].includes(data.status);
    ['reviewTitle','reviewContent','reviewNotes','reviewConfirmed','saveDocumentReview'].forEach(id=>el(id).disabled=!editable);
    el('publishDocument').disabled=data.category_code==='customers'||!data.reviewed_at||data.status!=='ready';el('retryDocument').hidden=!['failed','uploaded','processing'].includes(data.status);
    el('reviewNotes').required=data.status==='needs_review';
  }
  // Lấy chi tiết tài liệu rồi đưa khung xem trước vào vị trí dễ nhìn.
  async function open(id){render(await api('/api/documents/'+id));el('documentPreview').scrollIntoView({block:'start',behavior:'smooth'});}
  // Ngăn gửi thao tác trùng và gom lỗi API về cùng cách hiển thị.
  async function action(fn){if(busy)return;busy=true;try{await fn();}catch(error){tell(error.message,true);}finally{busy=false;}}
  el('documentUpload').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const file=el('documentFile').files[0];if(!file)throw new Error('Vui lòng chọn file.');
    // Kiểm tra loại và dung lượng ở giao diện trước khi gửi; backend vẫn kiểm tra lại.
    if(!/\.(pdf|docx|xlsx)$/i.test(file.name))throw new Error('Chỉ nhận PDF, DOCX hoặc XLSX.');
    if(file.size===0||file.size>10*1024*1024)throw new Error('File không được rỗng hoặc vượt quá 10 MB.');
    el('uploadDocumentButton').disabled=true;tell('Đang tải lên và trích xuất; tài liệu chưa được đưa vào kho tri thức.');
    // Gửi file multipart; nếu là file khách hàng đủ điều kiện thì tạo bản xem trước nhập liệu.
    try{const data=await api('/api/documents',{method:'POST',body:new FormData(event.target)});render(data);page=1;await refresh();tell(data.status==='failed'?data.error_message:'Đã trích xuất. Hãy đối chiếu nội dung và các cảnh báo.',data.status==='failed');if(data.category_code==='customers'&&canImport&&data.status!=='failed')await previewCustomers();}
    finally{el('uploadDocumentButton').disabled=false;}
  });});
  // Lưu nội dung đã đối chiếu cùng phiên bản để backend phát hiện cập nhật đồng thời.
  el('documentReview').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const data=await api('/api/documents/'+selected.id+'/review',{method:'PUT',...json({title:el('reviewTitle').value,content:el('reviewContent').value,notes:el('reviewNotes').value,confirmed:el('reviewConfirmed').checked,version:selected.version})});render(data);await refresh();tell('Đã lưu bản kiểm tra. Chưa đưa vào kho tri thức.');
  });});
  // Chỉ yêu cầu xuất bản phiên bản hiện tại; điều kiện review được kiểm tra lại ở backend.
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
  api('/api/documents/lookups').then(data=>{canImport=data.can_import_customers;for(const category of data.categories){const option=node('option',category.name);option.value=category.id;option.dataset.categoryCode=category.category_code;el('documentCategory').append(option);}if(data.all_branches){const option=node('option','Toàn hệ thống');option.value='';el('documentBranch').append(option);}for(const branch of data.branches){const option=node('option',branch.code+' · '+branch.name);option.value=branch.id;el('documentBranch').append(option);}return refresh();}).catch(error=>tell(error.message,true));

  // Tạo bản xem trước khách hàng và hiển thị lỗi theo từng dòng trước khi ghi CSDL.
  async function previewCustomers(){
    importBatch=await api('/api/customer-input',{method:'POST',...json({document_id:selected.id})});
    const box=el('customerImportPreview');box.replaceChildren();
    for(const warning of importBatch.warnings||[])box.append(node('p',warning));
    const table=node('table'),head=node('tr');for(const label of ['Dòng','Họ tên','SĐT','Email','Chi nhánh','Thao tác','Lỗi cần sửa'])head.append(node('th',label));table.append(head);
    for(const item of importBatch.rows){const tr=node('tr');for(const value of [item.row,item.data.full_name,item.data.phone,item.data.email,item.data.branch_code,item.action==='update'?'Cập nhật':'Thêm mới',item.errors.join(' ')])tr.append(node('td',value));table.append(tr);}box.append(table);
    el('customerImportFeedback').textContent=importBatch.status==='committed'?'Danh sách này đã được đồng bộ.':importBatch.valid?'Đã xem trước '+importBatch.rows.length+' dòng. Chưa cập nhật CSDL; hãy xác nhận bên dưới.':'Có dòng thiếu/sai thông tin. Mở “Kiểm tra và đồng bộ khách hàng” để chỉnh sửa trước khi lưu.';
    el('commitCustomerImport').disabled=!importBatch.valid||importBatch.status!=='draft';el('confirmCustomerImport').checked=false;
  }
  el('previewCustomerImport').addEventListener('click',()=>action(previewCustomers));
  el('commitCustomerImport').addEventListener('click',()=>action(async()=>{if(!el('confirmCustomerImport').checked)throw Error('Vui lòng đối chiếu và xác nhận danh sách.');el('commitCustomerImport').disabled=true;try{const result=await api('/api/customer-input/'+importBatch.id+'/commit',{method:'POST',...json({version:importBatch.version,confirmed:true})});el('customerImportFeedback').replaceChildren(node('p','Đã thêm '+result.created+' khách, cập nhật '+result.updated+' hồ sơ.'));const link=node('a','Xem danh sách khách hàng vừa đồng bộ');link.href='/customers?import_batch='+result.batch_id;el('customerImportFeedback').append(link);importBatch.status='committed';await refresh();}catch(error){el('commitCustomerImport').disabled=false;throw error;}}));
})();
