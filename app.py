import os
from src.utils import *
from dotenv import load_dotenv

from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from flask_dropzone import Dropzone

load_dotenv()

ALLOWED_EXTENSIONS = {'wav'}

app = Flask(__name__)

app.config['UPLOAD_PATH'] = os.getenv('UPLOAD_FOLDER')
# app.config.update(
#     # Flask-Dropzone config:
#     DROPZONE_ALLOWED_FILE_TYPE='audio',
#     DROPZONE_MAX_FILES=1,
#     DROPZONE_IN_FORM=True,
#     DROPZONE_UPLOAD_ON_CLICK=True,
#     DROPZONE_UPLOAD_ACTION='handle_upload',  # URL or endpoint
#     DROPZONE_UPLOAD_BTN_ID='submit',
# )

# Check if file have the good extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

dropzone = Dropzone(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html")

@app.route('/sign_up')
def sign_up():
    return render_template("sign_up.html")

@app.route('/forgot-password')
def forgot_password():
    return render_template("forgot-password.html")

@app.route('/account', methods=['POST'])
def account():
    """
    Route for account page with POST method.
    If state parameter is 'sign_in', checks if user exists in database with given username and password.
    If user exists, renders the account page with user details and files associated with the user.
    If state parameter is 'sign_up', adds the new user to the database with provided details and renders the account page with the new user details and files associated with the user.
    """

    state = request.values.get('state')
    if state == "sign_in":
        username = request.values.get('username')
        password = request.values.get('password')

        Database.open_connexion()
        user = Database.check_user(
            username=username,
            password=password
        )
        files = Database.get_files()
        Database.close_connexion()

        if isinstance(user, dict):
            return render_template('account.html', user=user, files=files)

    elif state == "sign_up":
        gender = request.values.get('gender')
        firstName = request.values.get('firstName')
        lastName = request.values.get('lastName')
        username = request.values.get('username')
        email = request.values.get('email')
        password = request.values.get('password')

        Database.open_connexion()
        Database.add_user(
            gender=gender,
            first_name=firstName,
            last_name=lastName,
            username=username,
            email=email,
            password=password
        )
        print("####################\n New user added ! \n####################")
        user = Database.check_user(
            username=username,
            password=password
        )
        files = Database.get_files()
        Database.close_connexion()
        
        return render_template('account.html', user=user, files=files)

# Modify this part
@app.route('/upload', methods=['POST'])
def handle_upload():
    
    for key, f in request.files.items():
        if key.startswith('file'):
            f.save(os.path.join(app.config['UPLOAD_PATH'], secure_filename(f.filename)))
    
    project_name = request.values.get('project')
    acquisition_date = request.values.get('acquisition_date')
    depth = request.values.get('depth')
    fs = request.values.get('fs')
    lat = request.values.get('lat')
    long = request.values.get('long')
    duration = None

    # Database.open_connexion()
    # Database.add_project(project_name, acquisition_date, depth, lat, long)
    # id_project = Database.get_projects(name=project_name)["id_project"]
    # Database.add_file(secure_filename(f.filename), acquisition_date, duration, fs, app.config['UPLOAD_PATH'], id_project)
    # Database.close_connexion()

    return '', 204
    

@app.route('/form', methods=['POST'])
def handle_form():
    title = request.form.get('title')
    description = request.form.get('description')
    return 'file uploaded and form submit<br>title: %s<br> description: %s' % (title, description)

if __name__ == "__main__":
    db = Database
    app.run(debug=True, port=5001)
