// Minimal JS for fetching and rendering internships/companies via the JSON API
// Uses fetch API and updates DOM. Keep small and dependency-free.

const state = {
  page: 1,
  per_page: 25,
  q: null
};

const companiesState = {
  page: 1,
  per_page: 25,
  q: null
};

function $(s){return document.querySelector(s)}

async function fetchInternships(){
  const params = new URLSearchParams({
    page: state.page,
    per_page: state.per_page,
    q: state.q || ''
  });
  const res = await fetch(`/api/internships?${params.toString()}`);
  const data = await res.json();
  return data;
}

function renderPagination(containerSelector, page, per_page, total, onPage){
  const container = document.querySelector(containerSelector);
  if(!container) return;
  container.innerHTML = '';
  if(!total || total <= per_page) return;

  const totalPages = Math.max(1, Math.ceil(total / per_page));

  function makeBtn(text, p, disabled){
    const btn = document.createElement('button');
    btn.className = `mx-1 px-3 py-1 rounded text-sm border ${disabled? 'opacity-50 cursor-not-allowed':''}`;
    btn.innerText = text;
    if(!disabled) btn.addEventListener('click', ()=> onPage(p));
    return btn;
  }

  // Prev
  container.appendChild(makeBtn('Prev', Math.max(1, page-1), page<=1));

  // page window
  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize/2));
  let end = Math.min(totalPages, start + windowSize - 1);
  if(end - start < windowSize - 1){ start = Math.max(1, end - windowSize + 1); }

  for(let p = start; p <= end; p++){
    const btn = makeBtn(p.toString(), p, false);
    if(p === page){ btn.classList.add('font-semibold', 'bg-gray-100'); }
    container.appendChild(btn);
  }

  // Next
  container.appendChild(makeBtn('Next', Math.min(totalPages, page+1), page>=totalPages));
}

function renderRows(items){
  const rows = $('#rows');
  rows.innerHTML = '';
  items.forEach(it =>{
    const tr = document.createElement('tr');
    tr.className = 'border-t hover:bg-gray-50';
    tr.innerHTML = `
      <td class="p-3 align-top text-xs">${escapeHtml(it.company||'')}</td>
      <td class="p-3 text-xs">${escapeHtml(it.title||'')}</td>
      <td class="p-3 text-xs ">${escapeHtml(it.location||'')}</td>
      <td class="p-3"><span class="px-2 py-1 rounded ${it.status==='Open'? 'bg-green-100 text-green-800':'bg-red-100 text-red-800'}">${escapeHtml(it.status)}</span></td>
      <td class="p-3 text-xs">${escapeHtml(it.created_at||'')}</td>
      <td class="p-3"><button class="openBtn btn-accent text-white px-2 py-1 rounded" data-id="${it.id}">View</button></td>
    `;
    rows.appendChild(tr);
  });
}

function escapeHtml(s){
  return String(s).replace(/[&<>\"]/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' })[c]);
}

async function loadPage(){
  const list = $('#list');
  $('#loading').style.display = 'block';
  $('#table').classList.add('hidden');
  try{
    const data = await fetchInternships();
    renderRows(data.items || []);
    $('#loading').style.display = 'none';
    $('#table').classList.remove('hidden');
    // render pagination
    renderPagination('#pagination', state.page, state.per_page, data.total || 0, (p)=>{ state.page = p; loadPage(); });
    // attach view handlers
    document.querySelectorAll('.openBtn').forEach(btn=>btn.addEventListener('click', async (e)=>{
      const id = e.currentTarget.dataset.id;
      const res = await fetch(`/api/internship/${id}`);
      const json = await res.json();
       
    
      
      showModal(json);
    }));
  }catch(err){
    console.error(err);
    $('#loading').innerText = 'Failed to load.';
  }
}

// TODO:  render mark down - enchance
function showModal(data) {
  const modal = $('#modal');
  const content = $('#modalContent');

  // 1. Parse markdown safely
  const rawMarkdown = data.description || '';
  const parsedHtml = marked.parse(rawMarkdown);
  const safeHtml = DOMPurify.sanitize(parsedHtml);

  // 2. Inject content
  content.innerHTML = `
        <span class="text-red">${escapeHtml(data.title)}</span>
        ${escapeHtml(data.company || '')}
    

    <div class="prose max-w-none">
      ${safeHtml}
    </div>
  `;

  // 3. Show modal
  modal.classList.remove('hidden');
  modal.style.display = 'flex';

  // 4. Close on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modalClose();
  });
}


function modalClose(){
  const modal = $('#modal');
  modal.classList.add('hidden');
  modal.style.display = 'none';
}

// Companies
async function fetchCompanies(page = companiesState.page){
  const params = new URLSearchParams({page: page, per_page: companiesState.per_page, q: $('#companySearch')? $('#companySearch').value : ''});
  const res = await fetch(`/api/companies?${params.toString()}`);
  return res.json();
}

function renderCompanies(items){
  const list = $('#companyList');
  list.innerHTML = '';
  items.forEach(c=>{
    const card = document.createElement('div');
    card.className = 'p-4 border rounded hover:shadow';
    card.innerHTML = `<h3 class="font-semibold">${escapeHtml(c.name)}</h3><p class="text-sm text-gray-500">${escapeHtml(c.industry||'')}</p><p class="text-sm mt-2">${escapeHtml((c.description||'').slice(0,200))}</p><div class="mt-2"><button class="companyOpen btn-accent text-white px-3 py-1 rounded" data-id="${c.id}">View</button></div>`;
    list.appendChild(card);
  });
  document.querySelectorAll('.companyOpen').forEach(b=>b.addEventListener('click', async e=>{
    const id = e.currentTarget.dataset.id;
    const res = await fetch(`/api/company/${id}`);
    const json = await res.json();
    showCompanyModal(json);
  }));
}

function showCompanyModal(data){
  const modal = $('#companyModal');
  const content = $('#companyModalContent');
  content.innerHTML = `<h3 class="text-xl font-semibold mb-2">${escapeHtml(data.name)}</h3><p class="text-sm text-gray-500">${escapeHtml(data.industry||'')}</p><div class="mt-4 prose">${escapeHtml(data.description||'')}</div>`;
  modal.classList.remove('hidden');
  modal.style.display = 'flex';
  modal.addEventListener('click', (e)=>{ if(e.target===modal) companyModalClose(); });
}
function companyModalClose(){ const m = $('#companyModal'); m.classList.add('hidden'); m.style.display='none'; }

// Initialize per page
document.addEventListener('DOMContentLoaded', ()=>
  {
  if(window.PAGE_TYPE === 'internships'){
    $('#search').addEventListener('input', (e)=>{ state.q = e.target.value; state.page = 1; loadPage(); });
    $('#applyFilters').addEventListener('click', ()=>{ state.page=1; loadPage(); });
    $('#exportCsv').addEventListener('click', ()=>{ window.location = '/export/internships.csv'; });
    loadPage();
  }
  if(window.PAGE_TYPE === 'companies'){
    $('#companySearch').addEventListener('input', ()=>
      { companiesState.page = 1; fetchCompanies().then(d=>{ renderCompanies(d.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, d.total || 0, (p)=>{ companiesState.page = p; fetchCompanies(p).then(dd=>{ renderCompanies(dd.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, dd.total || 0, (n)=>{ companiesState.page = n; fetchCompanies(n).then(ddd=>{ renderCompanies(ddd.items||[]); }); }); }); }); })});
    
    $('#exportCompanies').addEventListener('click', ()=>{ window.location = '/export/internships.csv'; });
    // initial load
    fetchCompanies().then(d=>{ renderCompanies(d.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, d.total || 0, (p)=>{ companiesState.page = p; fetchCompanies(p).then(dd=>{ renderCompanies(dd.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, dd.total || 0, (n)=>{ companiesState.page = n; fetchCompanies(n).then(ddd=>{ renderCompanies(ddd.items||[]); }); }); }); }); });
  }});
