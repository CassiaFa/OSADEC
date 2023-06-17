import os
from src.utils import *
from dotenv import load_dotenv
from src.utils.compute_pipline import pipeline

from flask import Flask, render_template, request, send_from_directory, jsonify, make_response, redirect
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO

import pandas as pd

from datetime import datetime

import soundfile as sf

load_dotenv()

ALLOWED_EXTENSIONS = {'wav'}

app = Flask(__name__)

app.config['UPLOAD_PATH'] = os.getenv('UPLOAD_FOLDER')
app.config['SECRET_KEY'] = os.getenv('SOCKET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")

user = None
state = None

# Check if file have the good extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
@app.route("/<deconnexion>")
def index(deconnexion=None):
    global user
    global state
    
    if deconnexion=="deconnected":
        user = None
        state = None

    return render_template("index.html")

@app.route("/sign_in")
def sign_in():
    global user
    global state

    if state == "connected":
        return redirect("/account", code=302)
    else:
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

        resp.headers["Content-Disposition"] = f"attachment; filename={file[:-4]}.csv"

        return resp

# @app.route('/sign_in/account', methods=['GET', 'POST'])
@app.route('/account', methods=['GET', 'POST'])
def account():
    """
    Route for account page with POST method.
    If state parameter is 'sign_in', checks if user exists in database with given username and password.
    If user exists, renders the account page with user details and files associated with the user.
    If state parameter is 'sign_up', adds the new user to the database with provided details and renders the account page with the new user details and files associated with the user.
    """
    global user
    global state

    if isinstance(user, dict):
        Database.open_connexion()

        files = Database.get_files()
                
        projects = [p["name"] for p in Database.get_projects()]

        Database.close_connexion()

        return render_template('account.html', user=user, files=files, projects=projects)
    else :

        state = request.values.get('state')
        if state == "sign_in":
            username = request.values.get('username')
            password = request.values.get('password')

            Database.open_connexion()
            user = Database.check_user(
                username=username,
                password=password
            )
            Database.close_connexion()
            
            if isinstance(user, dict):
                Database.open_connexion()

                files = Database.get_files()
                
                projects = [p["name"] for p in Database.get_projects()]

                Database.close_connexion()
                
                state = "connected"

                user['registration_date'] = user['registration_date'].strftime('%Y-%m-%d')
                
                return render_template('account.html', user=user, files=files, projects=projects)
            else:
                return render_template('sign_in.html')

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
            
            user['registration_date'] = user['registration_date'].strftime('%Y-%m-%d')

            state = "connected"
            return render_template('account.html', user=user, files=files, projects=projects)
        else:
            return render_template('sign_in.html')


@socketio.on('connect', namespace='/progress')
def handle_connect():
    print('Client connected')

# Modify this part
@app.route('/upload', methods=['POST'])
def handle_upload():
    
    # Step 1: Upload file

    socketio.emit('progress', {'percent':0, 'message' : 'Uploading file ...', 'status':'loading'}, namespace='/progress')

    for key, f in request.files.items():
        file_name = secure_filename(f.filename)
        file_path = os.path.join(app.config['UPLOAD_PATH'], file_name)
        if key.startswith('file'):
            f.save(file_path)

            print(f"{file_path} uploaded")

    socketio.emit('progress', {'percent':25, 'message' : 'File uploaded', 'status':'loading'}, namespace='/progress')

    # Step 2: Write file information in the database

    socketio.emit('progress', {'percent':25, 'message' : 'Writing file information ...', 'status':'loading'}, namespace='/progress')

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

    socketio.emit('progress', {'percent':50, 'message' : 'File information written', 'status':'loading'}, namespace='/progress')

    # Step 3: Compute the detection pipeline on the file

    socketio.emit('progress', {'percent':50, 'message' : 'Computing detection pipeline ...', 'status':'loading'}, namespace='/progress')

    print("Pipeline started")
    result = pipeline(file_path, datetime.strptime(acquisition_date, '%Y-%m-%dT%H:%M:%S'), duration, fs)

    socketio.emit('progress', {'percent':75, 'message' : 'Pipeline finished', 'status':'loading'}, namespace='/progress')

    # Step 4: Write the result of detection to the database
    
    socketio.emit('progress', {'percent':75 , 'message' : 'Writing detections ...', 'status':'loading'}, namespace='/progress')

    for det in result:
        Database.add_detection(det["start"], det["end"], det["confidence"], det["id_species"], id_file)

    if len(result) > 0:
        print("Detections added to database")
    else:
        print("No detections")

    Database.close_connexion()

    socketio.emit('progress', {'percent':100, 'message' : 'Detections written', 'status':'loading'}, namespace='/progress')

    socketio.emit('progress', {'percent':100, 'message' : 'Progress finished', 'status':'complete'}, namespace='/progress')

    return '', 200
    
@app.route('/form', methods=['POST'])
def handle_form():
    title = request.form.get('title')
    description = request.form.get('description')
    return 'file uploaded and form submit<br>title: %s<br> description: %s' % (title, description)

if __name__ == "__main__":
    socketio.run(app=app, debug=True, host='0.0.0.0', port=5000)
