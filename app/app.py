import os
from src.utils import *
from dotenv import load_dotenv
from src.utils.compute_pipline import pipeline

from flask import Flask, render_template, request, send_from_directory, jsonify, make_response
from werkzeug.utils import secure_filename

import pandas as pd

from datetime import datetime
import time
import json

import soundfile as sf

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

@app.route('/file_info/<filename>')
def get_info(filename):
    
    Database.open_connexion()
    # Get file info
    file_info = Database.get_all_info(filename)
    
    Database.close_connexion()
    
    return jsonify(file_info)

@app.route('/account/<type>/<path:file>')
@app.route('/account/<type>/<int:id>/<path:file>')
def download_file(type, file, id=None):
    if type == "wav":
        return send_from_directory(app.config['UPLOAD_PATH'], file, as_attachment=True)
    elif type == 'csv':
        Database.open_connexion()
        result = Database.get_detections(id_file=id)
        Database.close_connexion()
        data = []
        for row in result:
            data.append([row['start'].strftime("%y-%m-%d %H:%M:%S"), row['stop'].strftime("%y-%m-%d %H:%M:%S"), row['confidence']])

        df = pd.DataFrame(data, columns=['start', 'end', 'confidence'], index=None)

        resp = make_response(df.to_csv())

        resp.headers["Content-Disposition"] = "attachment; filename=results.csv"

        return resp

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
        projects = [p["name"] for p in Database.get_projects()]
        Database.close_connexion()

        if isinstance(user, dict):
            return render_template('account.html', user=user, files=files, projects=projects)

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
        projects = [p["name"] for p in Database.get_projects()]
        Database.close_connexion()
        
        return render_template('account.html', user=user, files=files, projects=projects)

# Modify this part
@app.route('/upload', methods=['POST'])
def handle_upload():
    
    # Step 1: Upload file

    # file_progress = 0
    # total_steps = 4
    # progress_data = {'file': file_progress}


    for key, f in request.files.items():
        file_name = secure_filename(f.filename)
        file_path = os.path.join(app.config['UPLOAD_PATH'], file_name)
        if key.startswith('file'):
            f.save(file_path)

            print(f"{file_path} uploaded")

    # progress_data['file'] = 1
    
    # Step 2: Write file information in the database

    project_name = request.values.get('project')
    acquisition_date = request.values.get('acquisition_date')
    depth = request.values.get('depth')
    lat = request.values.get('lat')
    long = request.values.get('long')

    s = sf.SoundFile(file_path)
    fs = s.samplerate
    duration = s.frames / fs

    Database.open_connexion()

    if not Database.get_projects(name=project_name):
        Database.add_project(project_name, depth, lat, long)
        print(f"Project {project_name} added to database")
    
    id_project = Database.get_projects(name=project_name)["id_project"]
    print(f"Project {project_name} have id {id_project}")
    
    Database.add_file(file_name, acquisition_date, duration, fs, app.config['UPLOAD_PATH'], id_project)

    id_file = Database.get_files(name=file_name)["id_file"]

    print(f"File {file_name} added to database with id {id_file}")

    # progress_data['write_db'] = 1
    
    # send_progress(progress_data)  # Send progress update to frontend

    # Step 3: Compute the detection pipeline on the file

    print("Pipeline started")
    result = pipeline(file_path, datetime.strptime(acquisition_date, '%Y-%m-%dT%H:%M:%S'), duration, fs)

    # progress_data['pipeline'] = 1
    # send_progress(progress_data)  # Send progress update to frontend

    # Step 4: Write the result of detection to the database
    
    for det in result:
        Database.add_detection(det["start"], det["end"], det["confidence"], det["id_species"], id_file)

    if len(result) > 0:
        print("Detections added to database")
    else:
        print("No detections")
    # progress_data['write_detection'] = 1
    # send_progress(progress_data)  # Send progress update to frontend

    Database.close_connexion()
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
