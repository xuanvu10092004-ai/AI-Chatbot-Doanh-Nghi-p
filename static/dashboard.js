'use strict';
document.querySelectorAll('[data-widget]').forEach(widget=>{
  let chart;
  const load=async()=>{
    const content=widget.querySelector('.widget-content');content.textContent='Đang tải…';if(chart)chart.destroy();
    try{const response=await fetch('/api/dashboard/'+widget.dataset.widget);if(!response.ok)throw Error();const {rows}=await response.json();
      if(!rows.length){content.textContent='Chưa có dữ liệu.';return;}content.textContent='';
      if('label' in rows[0]){const canvas=document.createElement('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label',widget.querySelector('h2').textContent);content.append(canvas);chart=new Chart(canvas,{type:'bar',data:{labels:rows.map(r=>r.label||'Chưa xác định'),datasets:[{label:widget.querySelector('h2').textContent,data:rows.map(r=>Number(r.value)),backgroundColor:'#C8102E'}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});const list=document.createElement('p');list.textContent=rows.map(r=>(r.label||'Chưa xác định')+': '+new Intl.NumberFormat('vi-VN').format(Number(r.value))).join(' · ');content.append(list);}
      else{const labels={net_revenue:'Doanh thu thuần',orders:'Số đơn',total_stock:'Số xe tồn',empty_rows:'Dòng hết hàng',customers:'Số khách'};for(const [key,value] of Object.entries(rows[0])){const p=document.createElement('p');p.className='kpi';p.textContent=(labels[key]||key)+': '+new Intl.NumberFormat('vi-VN').format(Number(value))+(key==='net_revenue'?' VNĐ':'');content.append(p);}}
    }catch(error){content.textContent='Không tải được dữ liệu. Hãy thử lại.';}
  };widget.querySelector('.retry').addEventListener('click',load);load();
});
