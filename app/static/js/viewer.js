/*
 * Phase 4 redesign: spectrogram + detection review viewer (Main.dc.html).
 *
 * Consumes the Phase 3 `/api` contract (app/src/api/records.py) only:
 *   GET   /api/records/<id>/spectrogram?start=&end=&fmin=&fmax=  -> PNG + X-Axis-* headers
 *   GET   /api/records/<id>/detections                           -> {detections: [...]}
 *   PATCH /api/detections/<id>                                   -> {review_status}
 *
 * The pixel <-> (time, frequency) mapping below is exactly the formula
 * documented in `Spectrogram.axis_bounds()` (app/src/utils/pixlabel.py):
 *
 *   px = pixel_x + (t - time_start) / (time_end - time_start) * pixel_width
 *   py = pixel_y + (freq_max - f) / (freq_max - freq_min) * pixel_height
 *
 * No server math is duplicated here beyond that documented formula - the
 * geometry always comes from the response headers, never recomputed from
 * STFT parameters client-side.
 */

(function () {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';

  const page = document.getElementById('viewer-page');
  if (!page) return;

  const duration = parseFloat(page.dataset.duration) || 0;
  const wavUrl = page.dataset.wavUrl;
  const detectionsUrl = page.dataset.detectionsUrl;
  const spectrogramUrl = page.dataset.spectrogramUrl;

  const DEFAULT_FMIN = 15;
  const DEFAULT_FMAX = 200;
  const MIN_WINDOW_SECONDS = 2;
  // Mirrors the server's own DEFAULT_WINDOW_SECONDS (records.py): real records
  // can be multi-day recordings, so "zoom out"/"reset" must never ask the
  // (CPU-bound, uncached-on-first-hit) spectrogram endpoint to render the
  // whole file - only ever a bounded window.
  const MAX_WINDOW_SECONDS = Math.min(300, duration) || duration;
  const INITIAL_WINDOW_SECONDS = Math.min(60, duration) || duration;

  const state = {
    start: 0,
    end: INITIAL_WINDOW_SECONDS,
    fmin: DEFAULT_FMIN,
    fmax: DEFAULT_FMAX,
    colormap: 'ocean',
    bounds: null,
    detections: [],
    selectedId: null,
    hoveredId: null,
    minConfidence: 0,
    speciesFilter: '',
  };

  // ---- DOM refs ------------------------------------------------------
  const img = document.getElementById('spectrogram-img');
  const overlay = document.getElementById('detection-overlay');
  const wrap = document.getElementById('spectrogram-wrap');
  const statusEl = document.getElementById('spectrogram-status');
  const playhead = document.getElementById('playhead');
  const playheadTime = document.getElementById('playhead-time');
  const freqAxis = document.getElementById('freq-axis');
  const timeAxis = document.getElementById('time-axis');

  const audio = document.getElementById('audio-player');
  const btnPlay = document.getElementById('btn-play');
  const btnSkipBack = document.getElementById('btn-skip-back');
  const btnSkipFwd = document.getElementById('btn-skip-fwd');
  const transportTime = document.getElementById('transport-time');
  const speedSelect = document.getElementById('speed-select');
  const colormapSelect = document.getElementById('colormap-select');

  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomReset = document.getElementById('btn-zoom-reset');
  const timeWindowLabel = document.getElementById('time-window-label');
  const fminInput = document.getElementById('fmin-input');
  const fmaxInput = document.getElementById('fmax-input');
  const btnApplyFreq = document.getElementById('btn-apply-freq');

  const list = document.getElementById('detections-list');
  const countBadge = document.getElementById('detections-count-badge');
  const countMeta = document.getElementById('detection-count-meta');
  const statusPill = document.getElementById('record-status-pill');
  const reviewCounts = document.getElementById('review-counts');
  const btnSaveReview = document.getElementById('btn-save-review');
  const confidenceFilter = document.getElementById('confidence-filter');
  const confidenceValue = document.getElementById('confidence-value');
  const speciesFilterSelect = document.getElementById('species-filter');

  if (wavUrl) audio.src = wavUrl;
  img.dataset.colormap = state.colormap;

  // ---- Helpers ---------------------------------------------------------
  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) seconds = 0;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m + ':' + String(s).padStart(2, '0');
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function detectionVisible(d) {
    if (state.minConfidence && d.confidence < state.minConfidence) return false;
    if (state.speciesFilter && d.species !== state.speciesFilter) return false;
    return true;
  }

  // ---- Data loading ------------------------------------------------------
  function loadDetections() {
    return fetch(detectionsUrl)
      .then((r) => {
        if (!r.ok) throw new Error('detections request failed: ' + r.status);
        return r.json();
      })
      .then((data) => {
        state.detections = data.detections || [];
        populateSpeciesFilter();
        renderDetectionList();
        renderOverlay();
        updateCounts();
      })
      .catch((err) => {
        console.error(err);
        list.innerHTML = '<li class="detections-panel__empty">Could not load detections.</li>';
      });
  }

  function populateSpeciesFilter() {
    const species = Array.from(new Set(state.detections.map((d) => d.species).filter(Boolean))).sort();
    const current = speciesFilterSelect.value;
    speciesFilterSelect.innerHTML = '<option value="">All species</option>' +
      species.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
    if (species.includes(current)) speciesFilterSelect.value = current;
  }

  function loadSpectrogram() {
    statusEl.hidden = false;
    statusEl.textContent = 'Loading spectrogram…';
    const params = new URLSearchParams({
      start: state.start.toFixed(3),
      end: state.end.toFixed(3),
      fmin: state.fmin,
      fmax: state.fmax,
    });
    return fetch(`${spectrogramUrl}?${params.toString()}`)
      .then((r) => {
        if (!r.ok) throw new Error('spectrogram request failed: ' + r.status);
        const bounds = {
          timeStart: parseFloat(r.headers.get('X-Axis-Time-Start')),
          timeEnd: parseFloat(r.headers.get('X-Axis-Time-End')),
          freqMin: parseFloat(r.headers.get('X-Axis-Freq-Min')),
          freqMax: parseFloat(r.headers.get('X-Axis-Freq-Max')),
          pixelX: parseFloat(r.headers.get('X-Axis-Pixel-X')),
          pixelY: parseFloat(r.headers.get('X-Axis-Pixel-Y')),
          pixelWidth: parseFloat(r.headers.get('X-Axis-Pixel-Width')),
          pixelHeight: parseFloat(r.headers.get('X-Axis-Pixel-Height')),
          imageWidth: parseFloat(r.headers.get('X-Axis-Image-Width')),
          imageHeight: parseFloat(r.headers.get('X-Axis-Image-Height')),
        };
        return r.blob().then((blob) => ({ blob, bounds }));
      })
      .then(({ blob, bounds }) => {
        const previousUrl = img.dataset.objectUrl;
        const url = URL.createObjectURL(blob);
        img.onload = () => {
          if (previousUrl) URL.revokeObjectURL(previousUrl);
        };
        img.src = url;
        img.dataset.objectUrl = url;

        state.bounds = bounds;
        wrap.style.aspectRatio = `${bounds.imageWidth} / ${bounds.imageHeight}`;
        overlay.setAttribute('viewBox', `0 0 ${bounds.imageWidth} ${bounds.imageHeight}`);

        statusEl.hidden = true;
        fminInput.value = state.fmin;
        fmaxInput.value = state.fmax;
        timeWindowLabel.textContent = `${formatTime(state.start)} – ${formatTime(state.end)}`;

        renderAxes();
        renderOverlay();
        updatePlayhead();
      })
      .catch((err) => {
        statusEl.hidden = false;
        statusEl.textContent = 'Failed to load spectrogram.';
        console.error(err);
      });
  }

  // ---- Axes --------------------------------------------------------------
  function renderAxes() {
    const b = state.bounds;
    if (!b) return;

    timeAxis.innerHTML = '';
    const timeTicks = 7;
    for (let i = 0; i < timeTicks; i++) {
      const frac = i / (timeTicks - 1);
      const t = b.timeStart + frac * (b.timeEnd - b.timeStart);
      const leftPct = (b.pixelX + frac * b.pixelWidth) / b.imageWidth * 100;
      const span = document.createElement('span');
      span.className = 'axis-tick';
      span.style.left = leftPct + '%';
      span.textContent = formatTime(t);
      timeAxis.appendChild(span);
    }

    freqAxis.innerHTML = '';
    const freqTicks = 6;
    for (let i = 0; i < freqTicks; i++) {
      const frac = i / (freqTicks - 1);
      const f = b.freqMax - frac * (b.freqMax - b.freqMin);
      const topPct = (b.pixelY + frac * b.pixelHeight) / b.imageHeight * 100;
      const span = document.createElement('span');
      span.style.top = topPct + '%';
      span.textContent = Math.round(f);
      freqAxis.appendChild(span);
    }
  }

  // ---- Detection overlay ---------------------------------------------------
  function renderGrid(b) {
    const timeTicks = 7;
    for (let i = 1; i < timeTicks - 1; i++) {
      const x = b.pixelX + (i / (timeTicks - 1)) * b.pixelWidth;
      const line = document.createElementNS(SVG_NS, 'line');
      line.setAttribute('x1', x);
      line.setAttribute('x2', x);
      line.setAttribute('y1', b.pixelY);
      line.setAttribute('y2', b.pixelY + b.pixelHeight);
      line.classList.add('spectrogram-grid-line');
      overlay.appendChild(line);
    }
    const freqTicks = 6;
    for (let i = 1; i < freqTicks - 1; i++) {
      const y = b.pixelY + (i / (freqTicks - 1)) * b.pixelHeight;
      const line = document.createElementNS(SVG_NS, 'line');
      line.setAttribute('x1', b.pixelX);
      line.setAttribute('x2', b.pixelX + b.pixelWidth);
      line.setAttribute('y1', y);
      line.setAttribute('y2', y);
      line.classList.add('spectrogram-grid-line');
      overlay.appendChild(line);
    }
  }

  function renderOverlay() {
    const b = state.bounds;
    overlay.innerHTML = '';
    if (!b) return;

    renderGrid(b);

    const timeSpan = b.timeEnd - b.timeStart;
    const freqSpan = b.freqMax - b.freqMin;
    if (timeSpan <= 0 || freqSpan <= 0) return;

    state.detections.forEach((d) => {
      if (d.f_min == null || d.f_max == null) return;
      // Fully outside the current window/band: nothing to draw.
      if (d.t_end <= b.timeStart || d.t_start >= b.timeEnd) return;
      if (d.f_max <= b.freqMin || d.f_min >= b.freqMax) return;

      const tStart = Math.max(d.t_start, b.timeStart);
      const tEnd = Math.min(d.t_end, b.timeEnd);
      const fLow = Math.max(d.f_min, b.freqMin);
      const fHigh = Math.min(d.f_max, b.freqMax);

      const x = b.pixelX + (tStart - b.timeStart) / timeSpan * b.pixelWidth;
      const w = Math.max((tEnd - tStart) / timeSpan * b.pixelWidth, 1);
      const y = b.pixelY + (b.freqMax - fHigh) / freqSpan * b.pixelHeight;
      const h = Math.max((fHigh - fLow) / freqSpan * b.pixelHeight, 1);

      const visible = detectionVisible(d);

      const rect = document.createElementNS(SVG_NS, 'rect');
      rect.setAttribute('x', x);
      rect.setAttribute('y', y);
      rect.setAttribute('width', w);
      rect.setAttribute('height', h);
      rect.setAttribute('data-status', d.review_status);
      rect.dataset.id = d.id;
      rect.classList.add('detection-box');
      if (!visible) rect.classList.add('is-below-threshold');
      if (d.id === state.selectedId) rect.classList.add('is-selected');
      if (d.id === state.hoveredId) rect.classList.add('is-hovered');
      rect.addEventListener('mouseenter', () => setHovered(d.id));
      rect.addEventListener('mouseleave', () => setHovered(null));
      rect.addEventListener('click', () => selectDetection(d.id, { recenter: false }));
      overlay.appendChild(rect);

      const text = document.createElementNS(SVG_NS, 'text');
      text.setAttribute('x', x + 3);
      text.setAttribute('y', Math.max(y - 4, 10));
      text.textContent = `${d.species || 'Unknown'} · ${d.confidence.toFixed(2)}`;
      text.classList.add('detection-label');
      if (!visible) text.classList.add('is-below-threshold');
      overlay.appendChild(text);
    });
  }

  function setHovered(id) {
    if (state.hoveredId === id) return;
    state.hoveredId = id;
    updateHighlight();
  }

  function selectDetection(id, opts) {
    state.selectedId = id;
    updateHighlight();
    if (opts && opts.recenter) {
      const d = state.detections.find((x) => x.id === id);
      if (d) recenterOn(d);
    }
  }

  function updateHighlight() {
    overlay.querySelectorAll('.detection-box').forEach((el) => {
      const id = Number(el.dataset.id);
      el.classList.toggle('is-selected', id === state.selectedId);
      el.classList.toggle('is-hovered', id === state.hoveredId);
    });
    list.querySelectorAll('.detection-row').forEach((el) => {
      const id = Number(el.dataset.id);
      el.classList.toggle('is-selected', id === state.selectedId);
    });
  }

  function recenterOn(d) {
    const alreadyVisible = state.bounds &&
      d.t_start >= state.bounds.timeStart && d.t_end <= state.bounds.timeEnd;
    if (alreadyVisible) return;

    const span = Math.max(d.t_end - d.t_start, MIN_WINDOW_SECONDS);
    const pad = span; // one detection-width of padding on each side
    const start = Math.max(0, d.t_start - pad);
    const end = Math.min(duration, d.t_end + pad);
    state.start = start;
    state.end = end;
    loadSpectrogram();
  }

  // ---- Detection list -------------------------------------------------
  function renderDetectionList() {
    list.innerHTML = '';
    const filtered = state.detections.filter(detectionVisible);
    countBadge.textContent = filtered.length;
    countMeta.textContent = `${state.detections.length} detection${state.detections.length === 1 ? '' : 's'}`;

    if (filtered.length === 0) {
      const li = document.createElement('li');
      li.className = 'detections-panel__empty';
      li.textContent = state.detections.length === 0
        ? 'No detections for this record.'
        : 'No detections match the current filters.';
      list.appendChild(li);
      return;
    }

    filtered
      .slice()
      .sort((a, b) => a.t_start - b.t_start)
      .forEach((d) => list.appendChild(buildDetectionRow(d)));
  }

  function buildDetectionRow(d) {
    const li = document.createElement('li');
    li.className = 'detection-row';
    li.dataset.id = d.id;
    li.setAttribute('data-status', d.review_status);
    if (d.id === state.selectedId) li.classList.add('is-selected');

    const main = document.createElement('div');
    main.className = 'detection-row__main';
    main.innerHTML = `
      <span class="detection-row__dot"></span>
      <span class="detection-row__time">${formatTime(d.t_start)}–${formatTime(d.t_end)}</span>
      <span class="detection-row__species">${escapeHtml(d.species || 'Unknown')}</span>
      <span class="detection-row__confidence">
        <span class="detection-row__confidence-track"><span class="detection-row__confidence-fill" style="width:${Math.round(d.confidence * 100)}%"></span></span>
        <span class="detection-row__confidence-value">${d.confidence.toFixed(2)}</span>
      </span>
    `;
    li.appendChild(main);

    const actions = document.createElement('div');
    actions.className = 'detection-row__actions';
    const confirmLabel = d.review_status === 'confirmed' ? 'Confirmed' : 'Confirm';
    const rejectLabel = d.review_status === 'rejected' ? 'Rejected' : 'Reject';
    actions.innerHTML = `
      <button type="button" class="btn btn-secondary" data-action="confirm">${confirmLabel}</button>
      <button type="button" class="btn btn-secondary" data-action="reject">${rejectLabel}</button>
      <button type="button" class="btn btn-secondary" data-action="play">Play</button>
    `;
    li.appendChild(actions);

    li.addEventListener('click', (evt) => {
      if (evt.target.closest('[data-action]')) return;
      selectDetection(d.id, { recenter: true });
    });
    li.addEventListener('mouseenter', () => setHovered(d.id));
    li.addEventListener('mouseleave', () => setHovered(null));

    actions.querySelector('[data-action="confirm"]').addEventListener('click', (evt) => {
      evt.stopPropagation();
      updateReviewStatus(d.id, d.review_status === 'confirmed' ? 'pending' : 'confirmed');
    });
    actions.querySelector('[data-action="reject"]').addEventListener('click', (evt) => {
      evt.stopPropagation();
      updateReviewStatus(d.id, d.review_status === 'rejected' ? 'pending' : 'rejected');
    });
    actions.querySelector('[data-action="play"]').addEventListener('click', (evt) => {
      evt.stopPropagation();
      playDetection(d);
    });

    return li;
  }

  function playDetection(d) {
    audio.currentTime = d.t_start;
    audio.playbackRate = parseFloat(speedSelect.value) || 1;
    audio.play();
    const stopAt = d.t_end;
    const onTime = () => {
      if (audio.currentTime >= stopAt) {
        audio.pause();
        audio.removeEventListener('timeupdate', onTime);
      }
    };
    audio.addEventListener('timeupdate', onTime);
  }

  // ---- Review status (confirm/reject + record status) ------------------
  function updateReviewStatus(id, reviewStatus) {
    return fetch(`/api/detections/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ review_status: reviewStatus }),
    })
      .then((r) => {
        if (!r.ok) throw new Error('update failed: ' + r.status);
        return r.json();
      })
      .then((updated) => {
        const d = state.detections.find((x) => x.id === id);
        if (d) d.review_status = updated.review_status;
        renderDetectionList();
        renderOverlay();
        updateHighlight();
        updateCounts();
      })
      .catch((err) => {
        console.error(err);
        window.alert('Could not update this detection (you may need to sign in again).');
      });
  }

  function updateCounts() {
    const total = state.detections.length;
    const confirmed = state.detections.filter((d) => d.review_status === 'confirmed').length;
    const rejected = state.detections.filter((d) => d.review_status === 'rejected').length;
    const pending = total - confirmed - rejected;
    reviewCounts.textContent = `${confirmed} conf · ${pending} pend · ${rejected} rej`;

    let status = 'New';
    let pillClass = 'pill-pending';
    if (total > 0 && pending === 0) {
      status = 'Reviewed';
      pillClass = 'pill-reviewed';
    } else if (pending < total) {
      status = 'In review';
      pillClass = 'pill-inreview';
    }
    statusPill.textContent = status;
    statusPill.className = `pill ${pillClass}`;
  }

  btnSaveReview.addEventListener('click', () => {
    btnSaveReview.disabled = true;
    const originalLabel = btnSaveReview.textContent;
    btnSaveReview.textContent = 'Saving…';
    loadDetections().finally(() => {
      btnSaveReview.textContent = 'Saved';
      setTimeout(() => {
        btnSaveReview.textContent = originalLabel;
        btnSaveReview.disabled = false;
      }, 1200);
    });
  });

  // ---- Transport (playback) ---------------------------------------------
  function updatePlayhead() {
    const b = state.bounds;
    const t = audio.currentTime || 0;
    transportTime.textContent = `${formatTime(t)} / ${formatTime(duration)}`;

    if (!b || t < b.timeStart || t > b.timeEnd) {
      playhead.hidden = true;
      return;
    }
    playhead.hidden = false;
    const leftPct = (b.pixelX + (t - b.timeStart) / (b.timeEnd - b.timeStart) * b.pixelWidth) / b.imageWidth * 100;
    playhead.style.left = leftPct + '%';
    playheadTime.textContent = formatTime(t);
  }

  audio.addEventListener('timeupdate', updatePlayhead);
  audio.addEventListener('loadedmetadata', updatePlayhead);
  audio.addEventListener('play', () => { btnPlay.innerHTML = '&#10074;&#10074;'; });
  audio.addEventListener('pause', () => { btnPlay.innerHTML = '&#9654;'; });

  btnPlay.addEventListener('click', () => {
    if (audio.paused) audio.play(); else audio.pause();
  });
  btnSkipBack.addEventListener('click', () => { audio.currentTime = Math.max(0, audio.currentTime - 5); });
  btnSkipFwd.addEventListener('click', () => { audio.currentTime = Math.min(duration, audio.currentTime + 5); });
  speedSelect.addEventListener('change', () => { audio.playbackRate = parseFloat(speedSelect.value) || 1; });
  colormapSelect.addEventListener('change', () => {
    state.colormap = colormapSelect.value;
    img.dataset.colormap = state.colormap;
  });

  // ---- Zoom (time) + frequency band ---------------------------------------
  function clampWindow(start, end) {
    start = Math.max(0, start);
    end = Math.min(duration, end);
    if (end - start < MIN_WINDOW_SECONDS) end = Math.min(duration, start + MIN_WINDOW_SECONDS);
    if (end - start > MAX_WINDOW_SECONDS) end = Math.min(duration, start + MAX_WINDOW_SECONDS);
    return [start, end];
  }

  btnZoomIn.addEventListener('click', () => {
    const center = (state.start + state.end) / 2;
    const newWidth = Math.max(MIN_WINDOW_SECONDS, (state.end - state.start) / 2);
    const [s, e] = clampWindow(center - newWidth / 2, center + newWidth / 2);
    state.start = s; state.end = e;
    loadSpectrogram();
  });

  btnZoomOut.addEventListener('click', () => {
    const center = (state.start + state.end) / 2;
    const newWidth = Math.min(MAX_WINDOW_SECONDS, (state.end - state.start) * 2);
    const [s, e] = clampWindow(center - newWidth / 2, center + newWidth / 2);
    state.start = s; state.end = e;
    loadSpectrogram();
  });

  btnZoomReset.addEventListener('click', () => {
    state.start = 0;
    state.end = MAX_WINDOW_SECONDS;
    loadSpectrogram();
  });

  btnApplyFreq.addEventListener('click', () => {
    const fmin = parseFloat(fminInput.value);
    const fmax = parseFloat(fmaxInput.value);
    if (!isFinite(fmin) || !isFinite(fmax) || fmin < 0 || fmax <= fmin) {
      window.alert('Invalid frequency range: fmin must be >= 0 and less than fmax.');
      return;
    }
    state.fmin = fmin;
    state.fmax = fmax;
    loadSpectrogram();
  });

  // ---- Filters ----------------------------------------------------------
  confidenceFilter.addEventListener('input', () => {
    state.minConfidence = parseFloat(confidenceFilter.value);
    confidenceValue.textContent = state.minConfidence.toFixed(2);
    renderDetectionList();
    renderOverlay();
  });

  speciesFilterSelect.addEventListener('change', () => {
    state.speciesFilter = speciesFilterSelect.value;
    renderDetectionList();
    renderOverlay();
  });

  // ---- Init ---------------------------------------------------------------
  loadDetections();
  loadSpectrogram();
})();
