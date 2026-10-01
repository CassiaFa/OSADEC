// Shared "app shell" behaviour for every signed-in screen that extends
// templates/app_base.html (dashboard, explorer, ...). Phase 2 of the redesign
// (docs/redesign/ROADMAP.md): populates the top-bar project switcher from
// `GET /api/projects` and keeps the current page's `?project=` query param in
// sync with it. Intentionally has no page-specific logic (that lives in
// dashboard.js / files.js) so it can be reused as-is by later phases.

// Small shared helpers (record status presentation, date/duration formatting)
// used by both dashboard.js and files.js, so the 3-state status model stays
// defined in one place (the strings/classes below are purely presentational;
// the actual `new` / `pending` / `reviewed` logic lives server-side in
// app/src/api/projects.py, see `_record_status`).
window.Osadec = {
  STATUS_LABEL: { new: 'New', pending: 'In review', reviewed: 'Reviewed' },
  STATUS_PILL: { new: 'pill-neutral', pending: 'pill-pending', reviewed: 'pill-reviewed' },

  formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  },

  formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return '—';
    const s = Math.round(seconds);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
  },

  statusPill(status) {
    const label = this.STATUS_LABEL[status] || status;
    const cls = this.STATUS_PILL[status] || 'pill-neutral';
    return `<span class="pill ${cls}">${label}</span>`;
  },
};

(function () {
  const select = document.getElementById('project-switcher');
  if (!select) return;

  const defaultProject = select.dataset.defaultProject || '';

  fetch('/api/projects')
    .then((res) => res.json())
    .then((data) => {
      const projects = data.projects || [];
      for (const project of projects) {
        const option = document.createElement('option');
        option.value = String(project.id);
        option.textContent = `${project.name} (${project.file_count})`;
        if (String(project.id) === String(defaultProject)) {
          option.selected = true;
        }
        select.appendChild(option);
      }
      if (!defaultProject) {
        select.value = '';
      }
    })
    .catch(() => {
      // Non-fatal: the page still works with whatever project the server
      // rendered by default, the switcher just stays empty.
    });

  select.addEventListener('change', () => {
    const url = new URL(window.location.href);
    if (select.value) {
      url.searchParams.set('project', select.value);
    } else {
      url.searchParams.delete('project');
    }
    window.location.href = url.toString();
  });
})();
