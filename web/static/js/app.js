// Minimal JS for fetching and rendering internships/companies via the JSON API
// Uses fetch API and updates DOM. Keep small and dependency-free.

const state = {
  page: 1,
  per_page: 25,
  q: null,
  // Advanced filters
  user_statuses: [],
  company_ids: [],
  locations: [],
  is_remote: null,
  status: null,
  site: null,
  sort_by: 'date_scraped',
  sort_order: 'desc',
  // Filter options cache
  filterOptions: null
};

const companiesState = {
  page: 1,
  per_page: 25,
  q: null
};

function $(s){return document.querySelector(s)}
function $$(s){return document.querySelectorAll(s)}

// =============================================================================
// FILTER OPTIONS & MULTI-SELECT
// =============================================================================

async function loadFilterOptions() {
  try {
    const res = await fetch('/api/internships/filters');
    state.filterOptions = await res.json();
    renderFilterDropdowns();
  } catch (err) {
    console.error('Failed to load filter options:', err);
  }
}

function renderFilterDropdowns() {
  const opts = state.filterOptions;
  if (!opts) return;

  // User Status options
  const userStatusContainer = $('#userStatusOptions');
  if (userStatusContainer) {
    userStatusContainer.innerHTML = '';
    const statusConfig = window.USER_STATUS_CONFIG || {};
    
    opts.user_status_options.forEach(s => {
      const config = statusConfig[s.value] || { label: s.label, color: 'bg-gray-100 text-gray-800' };
      const div = document.createElement('label');
      div.className = 'flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer';
      div.innerHTML = `
        <input type="checkbox" value="${s.value}" class="userStatusCheck rounded text-forest focus:ring-forest" />
        <span class="px-2 py-0.5 rounded text-xs ${config.color}">${config.label}</span>
      `;
      userStatusContainer.appendChild(div);
    });
  }

  // Company options
  const companyContainer = $('#companyOptions');
  if (companyContainer && opts.companies) {
    renderCompanyOptions(opts.companies);
  }

  // Location options
  const locationContainer = $('#locationOptions');
  if (locationContainer && opts.locations) {
    renderLocationOptions(opts.locations);
  }

  // Site/Source options
  const siteFilter = $('#siteFilter');
  if (siteFilter && opts.sites) {
    siteFilter.innerHTML = '<option value="">All sources</option>';
    opts.sites.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.site;
      opt.textContent = `${s.site} (${s.count})`;
      siteFilter.appendChild(opt);
    });
  }
}

function renderCompanyOptions(companies, filter = '') {
  const container = $('#companyOptions');
  if (!container) return;
  
  container.innerHTML = '';
  const filtered = filter 
    ? companies.filter(c => c.name.toLowerCase().includes(filter.toLowerCase()))
    : companies;
  
  filtered.slice(0, 50).forEach(c => {
    const div = document.createElement('label');
    div.className = 'flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer';
    div.innerHTML = `
      <input type="checkbox" value="${c.id}" class="companyCheck rounded text-forest focus:ring-forest" 
        ${state.company_ids.includes(c.id) ? 'checked' : ''} />
      <span class="text-sm truncate flex-1">${escapeHtml(c.name)}</span>
      <span class="text-xs text-gray-400">${c.count}</span>
    `;
    container.appendChild(div);
  });
  
  if (filtered.length > 50) {
    const more = document.createElement('div');
    more.className = 'text-xs text-gray-400 text-center py-2';
    more.textContent = `+${filtered.length - 50} more (use search)`;
    container.appendChild(more);
  }
}

function renderLocationOptions(locations, filter = '') {
  const container = $('#locationOptions');
  if (!container) return;
  
  container.innerHTML = '';
  const filtered = filter
    ? locations.filter(l => l.toLowerCase().includes(filter.toLowerCase()))
    : locations;
  
  filtered.slice(0, 50).forEach(loc => {
    const div = document.createElement('label');
    div.className = 'flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer';
    div.innerHTML = `
      <input type="checkbox" value="${escapeHtml(loc)}" class="locationCheck rounded text-forest focus:ring-forest"
        ${state.locations.includes(loc) ? 'checked' : ''} />
      <span class="text-sm truncate">${escapeHtml(loc)}</span>
    `;
    container.appendChild(div);
  });
  
  if (filtered.length > 50) {
    const more = document.createElement('div');
    more.className = 'text-xs text-gray-400 text-center py-2';
    more.textContent = `+${filtered.length - 50} more (use search)`;
    container.appendChild(more);
  }
}

function setupMultiSelectDropdown(btnId, dropdownId, searchId = null) {
  const btn = $(`#${btnId}`);
  const dropdown = $(`#${dropdownId}`);
  if (!btn || !dropdown) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    // Close other dropdowns
    $$('.multi-dropdown').forEach(d => {
      if (d !== dropdown) d.classList.add('hidden');
    });
    dropdown.classList.toggle('hidden');
  });

  dropdown.classList.add('multi-dropdown');

  // Search within dropdown
  if (searchId) {
    const searchInput = $(`#${searchId}`);
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const filter = e.target.value;
        if (dropdownId === 'companyDropdown') {
          renderCompanyOptions(state.filterOptions?.companies || [], filter);
        } else if (dropdownId === 'locationDropdown') {
          renderLocationOptions(state.filterOptions?.locations || [], filter);
        }
      });
      searchInput.addEventListener('click', (e) => e.stopPropagation());
    }
  }
}

function updateMultiSelectLabel(labelId, selected, allLabel) {
  const label = $(`#${labelId}`);
  if (!label) return;
  
  if (selected.length === 0) {
    label.textContent = allLabel;
  } else if (selected.length === 1) {
    label.textContent = selected[0].toString().length > 20 
      ? selected[0].toString().slice(0, 20) + '...' 
      : selected[0];
  } else {
    label.textContent = `${selected.length} selected`;
  }
}

function getActiveFilterCount() {
  let count = 0;
  if (state.user_statuses.length > 0) count++;
  if (state.company_ids.length > 0) count++;
  if (state.locations.length > 0) count++;
  if (state.is_remote !== null) count++;
  if (state.status) count++;
  if (state.site) count++;
  return count;
}

function updateFilterCount() {
  const count = getActiveFilterCount();
  const badge = $('#filterCount');
  if (badge) {
    if (count > 0) {
      badge.textContent = count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }
}

// =============================================================================
// INTERNSHIP STATUS UPDATE
// =============================================================================

async function updateInternshipStatus(internId, newStatus) {
  try {
    const res = await fetch(`/api/internship/${internId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_status: newStatus })
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to update status');
    }
    
    return true;
  } catch (err) {
    console.error('Status update failed:', err);
    alert('Failed to update status: ' + err.message);
    return false;
  }
}

function renderStatusDropdown(it) {
  const currentStatus = it.user_status || 'new';
  const config = window.USER_STATUS_CONFIG || {};
  const current = config[currentStatus] || { label: 'New', color: 'bg-gray-100 text-gray-800' };
  
  return `
    <div class="relative status-dropdown-container">
      <button 
        type="button"
        class="status-btn px-2 py-1 rounded text-xs ${current.color} hover:opacity-80 transition flex items-center gap-1"
        data-id="${it.id}"
        data-current="${currentStatus}"
      >
        <span>${current.label}</span>
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div class="status-dropdown hidden absolute z-30 mt-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]">
        ${Object.entries(config).map(([value, cfg]) => `
          <button 
            type="button"
            class="status-option w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50 flex items-center gap-2 ${value === currentStatus ? 'bg-gray-50' : ''}"
            data-value="${value}"
          >
            <span class="px-2 py-0.5 rounded ${cfg.color}">${cfg.label}</span>
          </button>
        `).join('')}
      </div>
    </div>
  `;
}

// =============================================================================
// FETCH & RENDER
// =============================================================================

async function fetchInternships(){
  const params = new URLSearchParams({
    page: state.page,
    per_page: state.per_page,
    sort_by: state.sort_by,
    sort_order: state.sort_order
  });
  
  if (state.q) params.set('q', state.q);
  if (state.status) params.set('status', state.status);
  if (state.site) params.set('site', state.site);
  if (state.is_remote !== null) params.set('is_remote', state.is_remote);
  if (state.user_statuses.length > 0) params.set('user_statuses', state.user_statuses.join(','));
  if (state.company_ids.length > 0) params.set('company_ids', state.company_ids.join(','));
  if (state.locations.length > 0) params.set('locations', state.locations.join(','));
  
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

function renderRows(items) {
  const rows = $('#rows');
  rows.innerHTML = '';

  const fragment = document.createDocumentFragment();

  for (const it of items) {
    const tr = document.createElement('tr');
    tr.className = 'border-t hover:bg-sage-light cursor-pointer transition';
    tr.dataset.id = it.id;

    const jobStatusClass =
      it.status === 'open'
        ? 'bg-green-100 text-green-800'
        : 'bg-red-100 text-red-800';

    tr.innerHTML = `
      <td class="p-3" onclick="event.stopPropagation()">
        ${renderStatusDropdown(it)}
      </td>

      <td class="p-3 align-top text-xs">
        ${renderCompanyCell(it)}
      </td>

      <td class="p-3 text-xs font-medium">
        <a href="/internship/${it.id}" class="hover:underline text-forest" onclick="event.stopPropagation()">
          ${escapeHtml(it.title || '')}
        </a>
      </td>

      <td class="p-3 text-xs text-gray-600">
        ${escapeHtml(it.location || '')}
      </td>

      <td class="p-3">
        ${renderBadges(it)}
      </td>

      <td class="p-3">
        <span class="px-2 py-1 rounded text-xs ${jobStatusClass}">
          ${escapeHtml(it.status || 'unknown')}
        </span>
      </td>

      <td class="p-3 text-xs text-gray-500">
        ${formatDate(it.date_scraped || it.created_at)}
      </td>

      <td class="p-3">
        <div class="flex gap-1">
          <button
            class="openBtn btn-accent text-white px-2 py-1 rounded text-xs"
            data-id="${it.id}"
            onclick="event.stopPropagation()"
            title="View Description"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </button>
          ${it.job_url ? `
            <a
              href="${escapeHtml(it.job_url)}"
              target="_blank"
              rel="noopener"
              class="btn-accent-dark text-white px-2 py-1 rounded text-xs"
              onclick="event.stopPropagation()"
              title="Apply"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          ` : ''}
        </div>
      </td>
    `;

    tr.addEventListener('click', () => {
      window.location.href = `/internship/${it.id}`;
    });

    fragment.appendChild(tr);
  }

  rows.appendChild(fragment);
  
  // Setup status dropdowns after render
  setupStatusDropdowns();
}

function setupStatusDropdowns() {
  // Handle status button clicks
  $$('.status-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const container = btn.closest('.status-dropdown-container');
      const dropdown = container.querySelector('.status-dropdown');
      
      // Close other dropdowns
      $$('.status-dropdown').forEach(d => {
        if (d !== dropdown) d.classList.add('hidden');
      });
      
      dropdown.classList.toggle('hidden');
    });
  });
  
  // Handle status option clicks
  $$('.status-option').forEach(opt => {
    opt.addEventListener('click', async (e) => {
      e.stopPropagation();
      const container = opt.closest('.status-dropdown-container');
      const btn = container.querySelector('.status-btn');
      const dropdown = container.querySelector('.status-dropdown');
      const internId = btn.dataset.id;
      const newStatus = opt.dataset.value;
      
      dropdown.classList.add('hidden');
      
      // Update on server
      const success = await updateInternshipStatus(internId, newStatus);
      if (success) {
        // Reload to show updated status
        loadPage();
      }
    });
  });
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return escapeHtml(dateStr);
  }
}

function renderCompanyCell(it) {
  if (!it.company_name && !it.company) {
    return '<span class="text-gray-400">Unknown</span>';
  }

  return `
    <a
      href="/company/${it.company_id || ''}"
      class="text-forest hover:underline"
      onclick="event.stopPropagation()"
    >
      ${escapeHtml(it.company_name || it.company)}
    </a>
  `;
}

function renderBadges(it) {
  let html = '';

  if (it.site) {
    html += `
      <span class="px-2 py-1 rounded bg-blue-100 text-blue-800 text-xs">
        ${escapeHtml(it.site)}
      </span>
    `;
  }

  if (it.is_remote) {
    html += `
      <span class="px-2 py-1 rounded bg-purple-100 text-purple-800 text-xs ml-1">
        Remote
      </span>
    `;
  }

  return html;
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
    const card = document.createElement('a');
    card.href = `/company/${c.id}`;
    card.className = 'block p-4 border rounded hover:shadow hover:border-forest transition bg-white';
    card.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="w-12 h-12 rounded-lg bg-sage-light flex items-center justify-center shrink-0">
          <i class="fas fa-building text-xl text-forest"></i>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-gray-900">${escapeHtml(c.name)}</h3>
          <p class="text-sm text-forest">${escapeHtml(c.industry||'')}</p>
          <p class="text-sm text-gray-500 mt-1 line-clamp-2">${escapeHtml((c.description||'').slice(0,150))}</p>
          ${c.city || c.country ? `<p class="text-xs text-gray-400 mt-2"><i class="fas fa-map-marker-alt mr-1"></i>${escapeHtml(c.city || '')}${c.city && c.country ? ', ' : ''}${escapeHtml(c.country || '')}</p>` : ''}
        </div>
      </div>
    `;
    list.appendChild(card);
  });
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
    // Load filter options first
    loadFilterOptions();
    
    // Setup multi-select dropdowns
    setupMultiSelectDropdown('userStatusBtn', 'userStatusDropdown');
    setupMultiSelectDropdown('companyBtn', 'companyDropdown', 'companySearch');
    setupMultiSelectDropdown('locationBtn', 'locationDropdown', 'locationSearch');
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
      $$('.multi-dropdown, .status-dropdown').forEach(d => d.classList.add('hidden'));
    });
    
    // Toggle filters panel
    const toggleBtn = $('#toggleFilters');
    const filtersPanel = $('#filtersPanel');
    if (toggleBtn && filtersPanel) {
      toggleBtn.addEventListener('click', () => {
        filtersPanel.classList.toggle('hidden');
      });
    }
    
    // Search input with debounce
    let searchTimeout;
    $('#search').addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.q = e.target.value;
        state.page = 1;
        loadPage();
      }, 300);
    });
    
    // Apply filters button
    $('#applyFilters').addEventListener('click', () => {
      // Collect multi-select values
      state.user_statuses = [...$$('.userStatusCheck:checked')].map(c => c.value);
      state.company_ids = [...$$('.companyCheck:checked')].map(c => parseInt(c.value));
      state.locations = [...$$('.locationCheck:checked')].map(c => c.value);
      
      // Single select values
      state.is_remote = $('#remoteFilter').value === '' ? null : $('#remoteFilter').value === '1';
      state.status = $('#statusFilter').value || null;
      state.site = $('#siteFilter').value || null;
      state.sort_by = $('#sortBy').value || 'date_scraped';
      state.sort_order = $('#sortOrder').value || 'desc';
      
      // Update labels
      updateMultiSelectLabel('userStatusLabel', state.user_statuses, 'All statuses');
      updateMultiSelectLabel('companyLabel', 
        state.company_ids.map(id => {
          const c = state.filterOptions?.companies?.find(c => c.id === id);
          return c ? c.name : id;
        }), 
        'All companies'
      );
      updateMultiSelectLabel('locationLabel', state.locations, 'All locations');
      
      updateFilterCount();
      state.page = 1;
      loadPage();
    });
    
    // Clear filters
    $('#clearFilters')?.addEventListener('click', () => {
      // Reset state
      state.user_statuses = [];
      state.company_ids = [];
      state.locations = [];
      state.is_remote = null;
      state.status = null;
      state.site = null;
      state.sort_by = 'date_scraped';
      state.sort_order = 'desc';
      state.q = '';
      state.page = 1;
      
      // Reset UI
      $('#search').value = '';
      $$('.userStatusCheck, .companyCheck, .locationCheck').forEach(c => c.checked = false);
      $('#remoteFilter').value = '';
      $('#statusFilter').value = '';
      $('#siteFilter').value = '';
      $('#sortBy').value = 'date_scraped';
      $('#sortOrder').value = 'desc';
      
      // Update labels
      updateMultiSelectLabel('userStatusLabel', [], 'All statuses');
      updateMultiSelectLabel('companyLabel', [], 'All companies');
      updateMultiSelectLabel('locationLabel', [], 'All locations');
      
      updateFilterCount();
      loadPage();
    });
    
    // Export CSV
    $('#exportCsv').addEventListener('click', () => { 
      window.location = '/export/internships.csv'; 
    });
    
    // Initial load
    loadPage();
  }
  if(window.PAGE_TYPE === 'companies'){
    $('#companySearch').addEventListener('input', ()=>
      { companiesState.page = 1; fetchCompanies().then(d=>{ renderCompanies(d.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, d.total || 0, (p)=>{ companiesState.page = p; fetchCompanies(p).then(dd=>{ renderCompanies(dd.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, dd.total || 0, (n)=>{ companiesState.page = n; fetchCompanies(n).then(ddd=>{ renderCompanies(ddd.items||[]); }); }); }); }); })});
    
    $('#exportCompanies')?.addEventListener('click', ()=>{ window.location = '/export/internships.csv'; });
    // initial load
    fetchCompanies().then(d=>{ renderCompanies(d.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, d.total || 0, (p)=>{ companiesState.page = p; fetchCompanies(p).then(dd=>{ renderCompanies(dd.items || []); $('#companyLoading').style.display='none'; renderPagination('#companyPagination', companiesState.page, companiesState.per_page, dd.total || 0, (n)=>{ companiesState.page = n; fetchCompanies(n).then(ddd=>{ renderCompanies(ddd.items||[]); }); }); }); }); });
  }});
