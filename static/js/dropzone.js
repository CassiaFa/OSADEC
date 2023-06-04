// Add event listener to the dropzone
const dropzone = document.querySelector('#dropzone');
dropzone.addEventListener('click', function() {
  const fileInput = document.querySelector('#file');
  fileInput.click();
});
dropzone.addEventListener('mouseover', handleDropZoneMouseOver);

// Add event listener to the file input field
const fileInput = document.querySelector('#file');
fileInput.addEventListener('change', handleFileSelect);

// Add event listener to the form
const form = document.querySelector('#upload-form');
form.addEventListener('submit', handleSubmit);


let selectedFile = null;

function validateForm() {
  // Get the form and required fields
  const form = document.querySelector('form');
  const requiredFields = form.querySelectorAll('input[required]');

  // Check if all required fields are filled in
  let formValid = true;

  requiredFields.forEach(field => {
      if (!field.value) {
          formValid = false;
          field.classList.add('invalid');
      } else {
          field.classList.remove('invalid');
      }
  });

  console.log(formValid);
  // Check if a file has been uploaded
  if (selectedFile === null) {
      formValid = false;
      document.querySelector('#dropzone').classList.add('invalid');
  } else {
      document.querySelector('#dropzone').classList.remove('invalid');
  }
  console.log(formValid);
  
  return formValid;
}

function handleFileSelect() {
  const dropzone = document.querySelector('#dropzone');
  const fileInput = document.querySelector('#file');
  const fileName = fileInput.files[0].name;

  // Create a new element to hold the file name and icon
  const fileLabel = document.createElement('p');
  fileLabel.innerHTML = `<img src="static/images/sound_file_icon.png" width="30%"> ${fileName}`;

  // Replace the existing dropzone contents with the file label
  dropzone.innerHTML = '';
  dropzone.appendChild(fileLabel);

  // Store the selected file in a variable
  selectedFile = fileInput.files[0];

  console.log("handleFileSelect is ok");
}

function handleSubmit(event) {

  event.preventDefault();
  
  console.log("handleSubmit");
  console.log(selectedFile);
  
  if (validateForm()) {
    const formData = new FormData(event.target); // Get form data
    console.log(formData); // Log form data

    if (selectedFile) {
      formData.append('file', selectedFile); // Add file to form data
      console.log('File selected');
      console.log(formData); // Log form data
      uploadFile(formData); // Send form data with file
    } else {
      // Handle case where no file is selected
      console.log('No file selected');
      return false;
    }
  } else {
    console.log('Form not valid');
    return false;
  }
}


// ================
// UPLOAD FILE
// ================
function uploadFile(formData) {
  console.log(formData);
  
  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    // Handle response from server
  })
  .catch(error => {
    // Handle error
  });
}

//  ==============
//  DROP ZONE
//  ==============
function handleDropZoneMouseOver(event) {
  event.preventDefault();
  event.stopPropagation();

  const dropzone = document.querySelector('#dropzone');
  dropzone.style.cursor = "grab";
  dropzone.addEventListener('dragenter', handleDragEnter);
  dropzone.addEventListener('dragover', handleDragOver);
  dropzone.addEventListener('dragleave', handleDragLeave);
  dropzone.addEventListener('drop', handleDrop);
}

function handleDragEnter(event) {
  event.preventDefault();
  event.stopPropagation();

  // Add visual feedback to indicate that the drop zone is active
  this.classList.add('active');
}

function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
}

function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();

  // Remove visual feedback when the cursor leaves the drop zone
  this.classList.remove('active');
}

function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();

  // Remove visual feedback when the file is dropped
  this.classList.remove('active');

  // Get the dropped file and add it to the input element
  const fileInput = document.querySelector('#file');
  fileInput.files = event.dataTransfer.files;

  handleFileSelect(event);
  // // Update the file label with the new file name
  // const fileName = fileInput.files[0].name;
  // const fileLabel = this.querySelector('p');
  // fileLabel.innerHTML = `<i class="fas fa-file"></i> ${fileName}`;
}