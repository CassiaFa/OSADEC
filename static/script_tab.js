Array.from(document.querySelectorAll('.tabs')).forEach((tab_container, TabID) => {
    const registers = tab_container.querySelector('.tab-registers');
    const bodies = tab_container.querySelector('.tab-bodies');
  
    Array.from(registers.children).forEach((el, i) => {
      el.setAttribute('aria-controls', `${TabID}_${i}`)
      bodies.children[i]?.setAttribute('id', `${TabID}_${i}`)
    
      el.addEventListener('click', (ev) => {
        let activeRegister = registers.querySelector('.active-tab');
        activeRegister.classList.remove('active-tab')
        activeRegister = el;
        activeRegister.classList.add('active-tab')
        changeBody(registers, bodies, activeRegister)
      })
  })
})


function changeBody(registers, bodies, activeRegister) {
    Array.from(registers.children).forEach((el, i) => {
        if (bodies.children[i]) {
            bodies.children[i].style.display = el == activeRegister ? 'block' : 'none'
        }

        el.setAttribute('aria-expanded', el == activeRegister ? 'true' : 'false')
    })
}

// Form script

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


// Add event listener to the dropzone
const dropzone = document.querySelector('#dropzone');
dropzone.addEventListener('click', function() {
  const fileInput = document.querySelector('#file');
  fileInput.click();
});

// Add event listener to the file input field
const fileInput = document.querySelector('#file');
fileInput.addEventListener('change', handleFileSelect);

// Add event listener to the form
const form = document.querySelector('#upload-form');
form.addEventListener('submit', handleSubmit);


let selectedFile = null;

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
    if (selectedFile) {
      console.log('File selected');
      uploadFile(selectedFile);
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

function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  console.log(file);
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