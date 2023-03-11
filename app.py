from flask import Flask, render_template, request
from src.utils import *

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html")

@app.route('/sign_up')
def sign_up():
    return render_template("sign_up.html")

@app.route('/account', methods=['POST'])
def account():
    state = request.values.get('state')
    if state == "sign_in":
        username = request.values.get('username')
        password = request.values.get('password')

        Database.open_connexion()
        right = Database.check_user(
            username=username,
            password=password
        )
        print(right)
        Database.close_connexion()

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
        Database.close_connexion()

    return render_template('account.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template("forgot-password.html")

if __name__ == "__main__":
    db = Database
    app.run(debug=True, port=5001)