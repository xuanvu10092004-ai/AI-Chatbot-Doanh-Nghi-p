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
  const keys = Object.keys(rows[0]);
  for (const key of keys) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = labels[key] || key; head.append(th); }
  thead.append(head);
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const key of keys) { const td = document.createElement('td'); td.textContent = displayValue(key, row[key], td); tr.append(td); }
    body.append(tr);
  }
  table.append(thead, body); tableBox.replaceChildren(table);
}

async function load() {
  // Giữ bộ lọc hiện tại và thêm batch nhập nếu trang được mở từ lịch sử khách.
  tableBox.textContent = 'Đang tải…'; retryButton.disabled = true;
  const params = new URLSearchParams(new FormData(form)); params.set('page', page);
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
