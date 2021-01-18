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

# (COMPLETED) Register function
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

# (COMPLETED) Login function
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
        c.execute("SELECT * FROM housemates WHERE username = :username", {"username": request.form.get("username")})
        results = c.fetchall()

        # Check that the user exists, and that the password matches
        if len(results) != 1 or not check_password_hash(results[0][3], request.form.get("password")):
            return render_template("errorlogin.html")

        # if successful, recognize the user via their user_id
        session["user_id"] = results[0][0]
        return redirect("/")

# Homepage where users can see which tasks are assigned to them
@app.route("/")
@login_required
def index():
    """ Show all reserved tasks. Prospective: show weekly score. show reserved gym time """

    # Query the reserved list for the specific user.
    c.execute("""
    SELECT title, description, score FROM reserved WHERE user_id = :user_id
    """, {"user_id": session["user_id"]})

    rows = c.fetchall()

    # create a list to hold the task object
    user_reserved_tasks = []

    # append the object into the list for easier iteration
    for row in rows:
        user_reserved_tasks.append({
            "title": row[0],
            "description": row[1],
            "score": row[2]
        })

    return render_template("index.html", user_reserved_tasks=user_reserved_tasks)

# (COMPLETED) Reserve: Users can assign certain tasks to themselves
@app.route("/reserve", methods=["GET", "POST"])
@login_required
def reserve():
    """ A drop down where users can reserve a task """
    if request.method == "GET":

        # Display the tasks title and difficulty from the drop down
        rows = c.execute("""
        SELECT title, description, score FROM tasks WHERE user_id = 0;
        """)

        return render_template("reserve.html", tasks = [ row[0] + " (" + str(row[2]) + ") " for row in rows ])
    else:
        # variable to hold the selected task on the drop down
        selected_task = request.form.get("task_item")

        # find the index of the selected item to only receive the task title to search the task list
        search_count = 0
        for i in selected_task:
            if i != "(":
                search_count += 1
            else:
                break
        
        # to distiniguish from other tasks, we stop the index right before the paranthesis
        to_reserve = selected_task[:search_count - 1]

        # search throught he database for a task title that matches to_reserve
        c.execute("""
        SELECT task_id FROM tasks where title = :to_reserve;
        """, {"to_reserve": to_reserve})

        task_ind = c.fetchall()[0][0]

        # Change the user_id of the above task to the current user
        c.execute("""
        UPDATE tasks SET user_id = :user_id WHERE task_id = :task_id
        """, {"user_id": session["user_id"], "task_id": task_ind})

        conn.commit()

        # Add the task to the users reserved list
        c.execute("""
        SELECT title, description, score
        FROM tasks
        WHERE task_id = :task_id
        """, {"task_id": task_ind})

        # query results
        task_to_reserve = c.fetchall()[0]

        # assign title, description, and score
        title = task_to_reserve[0]
        description = task_to_reserve[1]
        score = task_to_reserve[2]

        # insert the task into the reserved databased under the users id
        c.execute("""
        INSERT INTO reserved (user_id, title, description, score) VALUES (?, ?, ?, ?)
        """, (session["user_id"], title, description, score))

        conn.commit()

        return redirect("/")



# (COMPLETED) Create: Users can create a task to add to the master list
@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """ Allow users to create a task and add the task to the master list to reserve """
    if request.method == "GET":
        return render_template("create.html")
    else:
        title = request.form.get("title")
        description = request.form.get("description")
        score = request.form.get("score")

        c.execute("INSERT INTO tasks (title, description, score) VALUES (?, ?, ?)",
                    (title, description, score))
        conn.commit()

        return redirect("/")

# Edit: Users can select and edit a task
@app.route("/edit")
@login_required
def edit():
    return render_template("edit.html")

# Delete: Users can delete tasks from the master list
@app.route("/delete")
@login_required
def delete():
    return render_template("delete.html")

# Gym: Users can reserve an amount of time to use the home gym
@app.route("/gym") 
@login_required
def gym():
    return render_template("gym.html")

# History: Users can view which tasks were completed and at what date/time
@app.route("/history")
@login_required
def history():
    return render_template("history.html")

# Logout Function
@app.route("/logout")
def logout():
    """ User's option to logout of the app """

    session.clear()
    return redirect("/")