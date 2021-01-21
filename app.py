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

# (COMPLETED) Homepage where users can see which tasks are assigned to them
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
    
    if len(user_reserved_tasks) == 0:
        user_reserved_tasks = [{
            "title": "---",
            "description": "Your Task list is empty. Please go to Reserve to assign tasks.",
            "score": 0
        }]

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
@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """ User will be able to select a task, and edit the task """
    if request.method == "GET":

        # Display a list of tasks that are not reserved vua dropdown
        rows = c.execute("""
        SELECT title, score FROM tasks WHERE user_id = 0;
        """)

        return render_template("edit.html", tasks = [row[0] + " (" + str(row[1]) + ") " for row in rows])
    else:
        
        # assign the selected item to a variable
        task_to_edit = request.form.get("task_id")

        # find the task_id in database via titling
        search_count = 0
        for i in task_to_edit:
            if i != "(":
                search_count += 1
            else:
                break
        
        # Distinguish the task by its title
        title_of_task_to_edit = task_to_edit[:search_count - 1]

        c.execute("""
        SELECT task_id, description, score FROM tasks WHERE title = :title_of_task_to_edit
        """, {"title_of_task_to_edit": title_of_task_to_edit})

        # Query the old values for the task
        rows = c.fetchall()
        edit_task_id = rows[0][0]
        old_desc = rows[0][1]
        old_score = rows[0][2]

        # assign each new value from USER to a variable
        title_new = request.form.get("task_title")
        desc_new = request.form.get("task_desc")
        score_new = request.form.get("task_score")

        # if any new values are empty, they should equal the old value
        if title_new == "":
            title_new = title_of_task_to_edit
        
        if desc_new == "":
            desc_new = old_desc
        
        if score_new == "":
            score_new = old_score

        # push the changes to the database by task_id
        c.execute("""
        UPDATE tasks SET title = :title_new, description = :desc_new, score = :score_new
        WHERE task_id = :edit_task_id
        """, {"title_new": title_new, "desc_new": desc_new, "score_new": score_new, "edit_task_id": edit_task_id})

        conn.commit()

        return redirect("/")

# Delete: Users can delete tasks from the master list
@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """ A drop down where users can delete a task """
    if request.method == "GET":

        # Display the tasks title and difficulty from the drop down
        rows = c.execute("""
        SELECT title, description, score FROM tasks WHERE user_id = 0;
        """)

        return render_template("delete.html", tasks = [ row[0] + " (" + str(row[2]) + ") " for row in rows ])
    else:
        # variable to hold the selected task from the drop down
        selected_task = request.form.get("task_item")

        # find the index of the selected item to only receive the task title to search the task list
        search_count = 0
        for i in selected_task:
            if i != "(":
                search_count += 1
            else:
                break
        
        # to distiniguish from other tasks, we stop the index right before the paranthesis
        task_title_only = selected_task[:search_count - 1]

        # search through the database for a task title that matches task_title_only
        c.execute("""
        SELECT task_id FROM tasks where title = :task_title_only;
        """, {"task_title_only": task_title_only})

        task_id_to_delete = c.fetchall()[0][0]

        # Delete the task by task_id
        c.execute("""
        DELETE FROM tasks WHERE task_id = :task_id_to_delete;  
        """, {"task_id_to_delete": task_id_to_delete})
        conn.commit()

        return redirect("/")

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