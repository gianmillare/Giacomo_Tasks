# Dependencies
from flask import Flask, render_template, redirect, request, session
from flask_session import Session
import sqlite3
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.wrappers import Response
from io import StringIO


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

conn = sqlite3.connect('giacomo.db', check_same_thread=False)
c = conn.cursor()

# Register function
@app.route("/register", methods=["GET", "POST"])
def register():
    """ Register a new user """
    if request.method == "GET":
        return render_template("register.html")
    else:
        if request.form.get("name") == "" or request.form.get("username") == "" or request.form.get("password") == "":
            return render_template("errorpage.html")
        elif request.form.get("password") != request.form.get("confirmation"):
            return render_template("errorpage.html")
        else:
            name = request.form.get("name")
            username = request.form.get("username")
            password = generate_password_hash(request.form.get("password"))
            try: 
                c.execute("INSERT INTO housemates (name, username, password) VALUES (?, ?, ?)", (name, username, password))
                conn.commit()
            except:
                return render_template("errorpage.html")
            
            return render_template("/register_success.html")

# Login function
@app.route("/login", methods=["GET", "POST"])
def login():
    """ Registered users may log into the app """

    session.clear()

    # if the request is a GET, return the html file
    if request.method == "GET":
        return render_template("login.html")
    else:
        # if username or password is empty, return the errorpage
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("errorlogin.html")
        
        # Search the entered username and password in the database
        c.execute("SELECT * FROM registrants WHERE username = :username", {"username": request.form.get("username")})
        results = c.fetchall()

        # Check that the user exists, and that the password matches
        if len(results) != 1 or not check_password_hash(results[0][2], request.form.get("password")):
            return render_template("errorlogin.html")

        # if successful, recognize the user via their user_id
        session["user_id"] = results[0][0]
        return redirect("/")

@app.route("/")
def index():
    return render_template("index.html")