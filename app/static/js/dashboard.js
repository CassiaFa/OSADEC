// Dashboard screen (Phase 2 of the redesign, docs/redesign/ROADMAP.md): fetches
// `/api/projects/<id>/stats` and `/api/projects/<id>/records` (app/src/api/projects.py)
// and fills in the static skeleton rendered by templates/dashboard.html. No
// business logic here beyond formatting - record status, species counts etc.
// are all computed server-side.

(function () {
  const idProject = window.OSADEC_PROJECT_ID;
  if (!idProject) return;

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderStats(data) {
    document.getElementById('dashboard-subtitle').textContent =
      `${data.project.name} · depth ${data.project.depth ?? '—'} m`;

    document.getElementById('stat-records').textContent = data.records;
    document.getElementById('stat-detections').textContent = data.detections.toLocaleString('en-US');
    document.getElementById('stat-hours').textContent = data.audio_hours;

    const pendingEl = document.getElementById('stat-pending');
    pendingEl.textContent = data.pending_detections > 0
      ? `${data.pending_detections.toLocaleString('en-US')} detections pending review`
      : 'All detections reviewed';

    document.getElementById('stat-species').textContent = data.species_count;
    document.getElementById('stat-species-names').textContent = data.species.map((s) => s.name).join(', ');

    const barsEl = document.getElementById('species-bars');
    if (!data.species.length) {
      barsEl.innerHTML = '<div class="empty-state">No detections yet.</div>';
      return;
    }
    const max = Math.max(...data.species.map((s) => s.count));
    barsEl.innerHTML = data.species.map((s) => `
      <div class="bar-row">
        <span class="bar-row__label">${escapeHtml(s.name)}</span>
        <span class="bar-track"><span class="bar-track__fill" style="width:${max ? (100 * s.count / max).toFixed(1) : 0}%"></span></span>
        <span class="bar-row__value value">${s.count.toLocaleString('en-US')}</span>
      </div>
    `).join('');
  }

  function renderRecentRecords(data) {
    const container = document.getElementById('recent-records');
    if (!data.records.length) {
      container.innerHTML = '<div class="empty-state">No records in this project yet.</div>';
      return;
    }
    container.innerHTML = data.records.map((r) => `
      <a class="record-row" href="/records/${r.id}/review">
        <span class="record-thumb ${r.detections === 0 ? 'record-thumb--empty' : ''}" aria-hidden="true"></span>
        <span class="record-row__name">
          <span class="value">${escapeHtml(r.name)}</span>
          <span class="record-row__project">${escapeHtml(r.project_name)}</span>
        </span>
        <span class="badge-count">${r.detections} det</span>
        ${window.Osadec.statusPill(r.status)}
        <span class="record-row__meta">${window.Osadec.formatDate(r.date)}</span>
      </a>
    `).join('');
  }

  fetch(`/api/projects/${idProject}/stats`)
    .then((res) => res.json())
    .then(renderStats)
    .catch(() => {
      document.getElementById('dashboard-subtitle').textContent = 'Could not load project stats.';
    });

  fetch(`/api/projects/${idProject}/records?sort=date&dir=desc&page_size=5`)
    .then((res) => res.json())
    .then(renderRecentRecords)
    .catch(() => {
      document.getElementById('recent-records').innerHTML = '<div class="empty-state">Could not load records.</div>';
    });
})();
