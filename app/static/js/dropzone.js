// Upload panel for the Analyse tab (templates/account.html).
//
// Phase 5 UI (docs/redesign/ROADMAP.md): the panel now goes through visible
// steps (Uploaded -> Spectrogram & detection -> Done) driven by the
// 'progress' Socket.IO events relayed from templates/account.html (see
// window.OsadecUpload.handleProgress below), and never reloads the page.
// On 'complete' it shows a link to the review screen; on 'error' it shows
// the server message and a way to start a new upload without reloading.
//
// Note: previously this file *and* inline `onsubmit="handleSubmit(event)"` /
// `onchange="handleFileSelect(this)"` attributes in account.html both bound
// the same handlers, so every submit/file-change fired twice (e.g. two
// POST /upload requests per click). The inline attributes have been removed
// from account.html; this module is now the single source of event binding.

const dropzone = document.querySelector('#dropzone');
const fileInput = document.querySelector('#file');
const form = document.querySelector('#upload-form');
const uploadLayout = document.querySelector('#upload-layout');
const progressPanel = document.querySelector('#progress-panel');
const selectedFileBox = document.querySelector('#selected-file');
const selectedFileName = document.querySelector('#selected-file-name');
const selectedFileSize = document.querySelector('#selected-file-size');
const selectedFileRemove = document.querySelector('#selected-file-remove');
const dropzoneText = document.querySelector('#dropzone-text');

const DROPZONE_DEFAULT_TEXT = dropzoneText ? dropzoneText.textContent : '';

let selectedFile = null;

// ================
// FILE SELECTION
// ================
function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function handleFileSelect() {
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;

  selectedFile = file;
  dropzone.classList.remove('invalid');

  if (selectedFileName) selectedFileName.textContent = file.name;
  if (selectedFileSize) selectedFileSize.textContent = formatFileSize(file.size);
  if (selectedFileBox) selectedFileBox.hidden = false;
  if (dropzoneText) dropzoneText.textContent = 'Click to choose a different file';
}

function clearSelectedFile() {
  selectedFile = null;
  fileInput.value = '';
  if (selectedFileBox) selectedFileBox.hidden = true;
  if (dropzoneText) dropzoneText.textContent = DROPZONE_DEFAULT_TEXT;
}

if (selectedFileRemove) {
  selectedFileRemove.addEventListener('click', (event) => {
    event.stopPropagation();
    clearSelectedFile();
    dropzone.focus();
  });
}

// Add event listener to the dropzone
dropzone.addEventListener('click', function () {
  fileInput.click();
});
// Keyboard activation (Enter / Space) for the role="button" dropzone.
dropzone.addEventListener('keydown', function (event) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    fileInput.click();
  }
});
dropzone.addEventListener('mouseover', handleDropZoneMouseOver);

// Add event listener to the file input field
fileInput.addEventListener('change', handleFileSelect);

// Add event listener to the form
form.addEventListener('submit', handleSubmit);

// ================
// VALIDATION
// ================
function validateForm() {
  const requiredFields = form.querySelectorAll('input[required]');

  let formValid = true;
  let firstInvalid = null;

  requiredFields.forEach((field) => {
    if (!field.value) {
      formValid = false;
      field.classList.add('invalid');
      if (!firstInvalid) firstInvalid = field;
    } else {
      field.classList.remove('invalid');
    }
  });

  if (selectedFile === null) {
    formValid = false;
    dropzone.classList.add('invalid');
    if (!firstInvalid) firstInvalid = dropzone;
  } else {
    dropzone.classList.remove('invalid');
  }

  // Accessibility: move focus to the first invalid field instead of just
  // silently refusing to submit.
  if (!formValid && firstInvalid) {
    firstInvalid.focus();
  }

  return formValid;
}

function handleSubmit(event) {
  event.preventDefault();

  if (!validateForm()) {
    return false;
  }

  // `selectedFile` tracks `fileInput.files[0]` for validation purposes, but
  // the file input is a real child of #upload-form, so `new FormData(form)`
  // already carries it under the "file" key - no need to append it a second
  // time (the previous version did, which silently uploaded the same bytes
  // twice per request).
  const formData = new FormData(form);

  uploadFile(formData);

  showProgressPanel();
  resetSteps();
  setStepState('uploaded', 'active');
  setProgress(0, 'Uploading file…');

  return undefined;
}

// ================
// UPLOAD FILE
// ================
function uploadFile(formData) {
  // Phase 5 (docs/redesign/ROADMAP.md): progress is now emitted by the server
  // to this client only, targeted at the Socket.IO connection id of its own
  // /progress namespace connection (set on `window.socketProgressId` by the
  // inline script in templates/account.html). Without it the server has no
  // single legitimate recipient to target and simply won't emit progress
  // events (the upload itself still completes).
  if (window.socketProgressId) {
    formData.append('sid', window.socketProgressId);
  }

  fetch('/upload', {
    method: 'POST',
    body: formData,
  })
    .then((response) => response.json().catch(() => ({})).then((data) => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
      // The request only confirms that the analysis job was accepted (202,
      // with a job_id) or rejected (4xx); the actual pipeline progress and
      // completion arrive asynchronously via the 'progress' socket event
      // (relayed to handleProgress below by templates/account.html).
      if (!ok) {
        console.error('Upload rejected', data);
        showError(data.message || 'Upload failed.');
        return;
      }
      console.log('Analysis job accepted', data);
    })
    .catch((error) => {
      console.error('Upload error', error);
      showError('Could not reach the server. Check your connection and try again.');
    });
}

// ================
// STEP PANEL
// ================
const STEP_ORDER = ['uploaded', 'analysing', 'done'];

function stepEl(step) {
  return progressPanel ? progressPanel.querySelector(`.upload-step[data-step="${step}"]`) : null;
}

function setStepState(step, state) {
  const el = stepEl(step);
  if (el) el.setAttribute('data-state', state);
}

function resetSteps() {
  STEP_ORDER.forEach((step) => setStepState(step, 'pending'));
  const successBox = document.querySelector('#upload-success');
  const errorBox = document.querySelector('#upload-error');
  if (successBox) successBox.hidden = true;
  if (errorBox) errorBox.hidden = true;
  const progressBar = document.querySelector('#progress-bar');
  if (progressBar) progressBar.hidden = false;
}

function showProgressPanel() {
  if (uploadLayout) uploadLayout.hidden = true;
  if (progressPanel) progressPanel.hidden = false;
}

function setProgress(percent, message) {
  const bar = document.querySelector('#bar');
  const status = document.querySelector('#progress-status');
  const track = document.querySelector('#progress');
  if (bar) bar.style.width = `${percent}%`;
  if (track) track.setAttribute('aria-valuenow', String(percent));
  if (status) status.textContent = message;
}

function showSuccess(idFile) {
  const progressBar = document.querySelector('#progress-bar');
  const successBox = document.querySelector('#upload-success');
  const reviewLink = document.querySelector('#review-link');
  if (progressBar) progressBar.hidden = true;
  if (reviewLink && idFile != null) {
    const template = window.OSADEC_REVIEW_URL_TEMPLATE || '/records/0/review';
    reviewLink.href = template.replace('/0/', `/${idFile}/`);
  }
  if (successBox) {
    successBox.hidden = false;
    // Move focus into the notification so screen reader / keyboard users
    // notice the job finished instead of having to discover it visually.
    successBox.focus();
  }
}

function showError(message) {
  const errorBox = document.querySelector('#upload-error');
  const errorMessage = document.querySelector('#upload-error-message');
  setStepState('analysing', 'error');
  if (errorMessage) errorMessage.textContent = message || 'Analysis failed. Please try again.';
  if (errorBox) {
    errorBox.hidden = false;
    errorBox.focus();
  }
}

function resetUploadPanel() {
  if (uploadLayout) uploadLayout.hidden = false;
  if (progressPanel) progressPanel.hidden = true;
  resetSteps();
  setProgress(0, '');
  clearSelectedFile();
  const submitBtn = document.querySelector('#submit');
  if (submitBtn) submitBtn.disabled = false;
  dropzone.focus();
}

const uploadAnotherBtn = document.querySelector('#upload-another');
const uploadRetryBtn = document.querySelector('#upload-retry');
if (uploadAnotherBtn) uploadAnotherBtn.addEventListener('click', resetUploadPanel);
if (uploadRetryBtn) uploadRetryBtn.addEventListener('click', resetUploadPanel);

// Called by the inline Socket.IO handler in templates/account.html for every
// 'progress' event ({ job_id, id_file, percent, message, status }).
function handleProgress(data) {
  const { percent, message, status, id_file: idFile } = data;

  setProgress(percent, message);
  setStepState('uploaded', 'done');

  if (status === 'error') {
    setStepState('analysing', 'error');
    setStepState('done', 'pending');
    showError(message);
    return;
  }

  if (status === 'complete') {
    setStepState('analysing', 'done');
    setStepState('done', 'done');
    showSuccess(idFile);
    return;
  }

  setStepState('analysing', 'active');
  setStepState('done', 'pending');
}

window.OsadecUpload = { handleProgress };

//  ==============
//  DROP ZONE
//  ==============
function handleDropZoneMouseOver(event) {
  event.preventDefault();
  event.stopPropagation();

  dropzone.style.cursor = 'grab';
  dropzone.addEventListener('dragenter', handleDragEnter);
  dropzone.addEventListener('dragover', handleDragOver);
  dropzone.addEventListener('dragleave', handleDragLeave);
  dropzone.addEventListener('drop', handleDrop);
}

function handleDragEnter(event) {
  event.preventDefault();
  event.stopPropagation();

  this.classList.add('active');
}

function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
}

function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();

  this.classList.remove('active');
}

function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();

  this.classList.remove('active');

  fileInput.files = event.dataTransfer.files;
  handleFileSelect();
}
