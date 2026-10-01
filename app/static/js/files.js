// Explorer screen (Phase 2 of the redesign, docs/redesign/ROADMAP.md): search,
// filter, sort and paginate the records of the current project, all served by
// `GET /api/projects/<id>/records` (app/src/api/projects.py). The server does
// all the filtering/sorting/pagination; this file only renders what it
// returns and keeps the URL query string (and so, the browser back button and
// reload) in sync with the current filters.

(function () {
  const idProject = window.OSADEC_PROJECT_ID;
  if (!idProject) return;

  const form = document.getElementById('filters');
  const qInput = document.getElementById('filter-q');
  const speciesSelect = document.getElementById('filter-species');
  const statusSelect = document.getElementById('filter-status');
  const sortSelect = document.getElementById('filter-sort');
  const body = document.getElementById('records-body');
  const totalBadge = document.getElementById('records-total');
  const paginationSummary = document.getElementById('pagination-summary');
  const paginationPages = document.getElementById('pagination-pages');

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  const initialParams = new URLSearchParams(window.location.search);
  qInput.value = initialParams.get('q') || '';
  if (initialParams.get('species')) speciesSelect.value = initialParams.get('species');
  if (initialParams.get('status')) statusSelect.value = initialParams.get('status');
  if (initialParams.get('sort')) sortSelect.value = initialParams.get('sort');
  let currentPage = parseInt(initialParams.get('page'), 10) || 1;

  // Species filter options come from the project's own detected species
  // (stats endpoint), so the dropdown never lists a species that can't match
  // anything in this project.
  fetch(`/api/projects/${idProject}/stats`)
    .then((res) => res.json())
    .then((data) => {
      for (const s of data.species) {
        const option = document.createElement('option');
        option.value = String(s.id);
        option.textContent = s.name;
        if (initialParams.get('species') === String(s.id)) option.selected = true;
        speciesSelect.appendChild(option);
      }
    })
    .catch(() => {});

  function currentFilters() {
    return {
      q: qInput.value.trim(),
      species: speciesSelect.value,
      status: statusSelect.value,
      sort: sortSelect.value,
    };
  }

  function syncUrl(page) {
    const url = new URL(window.location.href);
    const filters = currentFilters();
    for (const [key, value] of Object.entries(filters)) {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    if (page > 1) url.searchParams.set('page', String(page));
    else url.searchParams.delete('page');
    window.history.replaceState(null, '', url.toString());
  }

  function renderRows(records) {
    if (!records.length) {
      body.innerHTML = '<tr><td colspan="7"><div class="empty-state">No records match these filters.</div></td></tr>';
      return;
    }
    body.innerHTML = records.map((r) => `
      <tr>
        <td class="col-preview"><span class="record-thumb record-thumb--sm ${r.detections === 0 ? 'record-thumb--empty' : ''}" aria-hidden="true"></span></td>
        <td>
          <span class="value" style="display:block">${escapeHtml(r.name)}</span>
          <span class="record-row__project">${escapeHtml(r.project_name)}</span>
        </td>
        <td class="numeric">${window.Osadec.formatDate(r.date)}</td>
        <td class="numeric">${window.Osadec.formatDuration(r.duration_seconds)}</td>
        <td class="numeric">${r.detections}</td>
        <td>${window.Osadec.statusPill(r.status)}</td>
        <td class="col-actions">
          <a class="btn btn-ghost" href="/records/${r.id}/review" title="Review ${escapeHtml(r.name)}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
          </a>
        </td>
      </tr>
    `).join('');
  }

  function renderPagination(data) {
    const start = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1;
    const end = Math.min(data.total, data.page * data.page_size);
    paginationSummary.textContent = `Showing ${start}-${end} of ${data.total} records`;

    const pages = [];
    const windowSize = 2;
    for (let p = 1; p <= data.pages; p += 1) {
      if (p === 1 || p === data.pages || Math.abs(p - data.page) <= windowSize) {
        pages.push(p);
      } else if (pages[pages.length - 1] !== '…') {
        pages.push('…');
      }
    }

    paginationPages.innerHTML = pages.map((p) => {
      if (p === '…') return '<span class="pagination__page" aria-hidden="true" style="border:none;background:none">…</span>';
      const current = p === data.page;
      return `<button type="button" class="pagination__page" data-page="${p}" ${current ? 'aria-current="page"' : ''}>${p}</button>`;
    }).join('');

    paginationPages.querySelectorAll('button[data-page]').forEach((btn) => {
      btn.addEventListener('click', () => load(parseInt(btn.dataset.page, 10)));
    });
  }

  function load(page) {
    currentPage = page;
    const filters = currentFilters();
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.species) params.set('species', filters.species);
    if (filters.status) params.set('status', filters.status);
    params.set('sort', filters.sort);
    params.set('page', String(page));

    syncUrl(page);

    body.innerHTML = '<tr><td colspan="7"><div class="empty-state">Loading records&hellip;</div></td></tr>';

    fetch(`/api/projects/${idProject}/records?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        totalBadge.textContent = data.total;
        renderRows(data.records);
        renderPagination(data);
      })
      .catch(() => {
        body.innerHTML = '<tr><td colspan="7"><div class="empty-state">Could not load records.</div></td></tr>';
      });
  }

  form.addEventListener('submit', (e) => e.preventDefault());

  let debounce;
  qInput.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => load(1), 300);
  });
  speciesSelect.addEventListener('change', () => load(1));
  statusSelect.addEventListener('change', () => load(1));
  sortSelect.addEventListener('change', () => load(1));

  load(currentPage);
})();
