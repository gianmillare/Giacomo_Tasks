# Dependencies
from flask import Flask, render_template, redirect, request, session, flash
from flask_session import Session
import sqlite3
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.wrappers import Response
from io import StringIO
import calendar


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
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """ Show all reserved tasks. Prospective: show weekly score. show reserved gym time """
    # ------------ DISPLAY THE RESERVED TASKS SPECIFIC TO THE USER --------------------

    # Query the reserved list for the specific user.
    c.execute("""
    SELECT reserve_id, title, description, score FROM reserved WHERE user_id = :user_id
    """, {"user_id": session["user_id"]})

    rows = c.fetchall()

    # create a list to hold the task object
    user_reserved_tasks = []

    # append the object into the list for easier iteration
    for row in rows:
        user_reserved_tasks.append({
            "reserve_id": row[0],
            "title": row[1],
            "description": row[2],
            "score": row[3]
        })

    # ------------ DISPLAY THE COMPLETED TASKS UNDER THE RESERVED TASKS --------------------

    # Query the completed_tasks database with user_id
    c.execute("""
    SELECT title, score, completed_on FROM completed_tasks WHERE user_id = :user_id
    """, {"user_id": session["user_id"]})

    rows = c.fetchall()
    user_completed_tasks = []

    for row in rows:
        user_completed_tasks.append({
            "title": row[0],
            "score": row[1],
            "completed_on": row[2]
        })
    
    # ------------ DISPLAY THE RESERVED GYM TIMES OF EVERYONE --------------------
    c.execute("""
    SELECT name, start, end, date, reserve_id FROM housemates
    INNER JOIN reserved_gym
    ON housemates.id = reserved_gym.user_id
    """)

    results = c.fetchall()

    display_reserved_gym = []

    for i in results:
        display_reserved_gym.append({
            "reserve_id": i[4],
            "name": i[0],
            "start": i[1],
            "end": i[2],
            "date": i[3]
        })

    # ------------ DISPLAY THE SCOREBOARD --------------------
    c.execute("""
    SELECT name, sum(score) FROM housemates 
    INNER JOIN completed_tasks 
    ON housemates.id = completed_tasks.user_id
    GROUP BY name;
    """)

    results = c.fetchall()

    scoreboard = []

    for i in results:
        scoreboard.append({
            "name": i[0],
            "score": i[1]
        })
    
    if len(scoreboard) == 0:
        c.execute("""
        SELECT name FROM housemates
        """)

        results = c.fetchall()

        for i in results:
            scoreboard.append({
                "name": i[0],
                "score": 0
            })

    # ------------ DISPLAY THE AVAILABLE TASKS LIST --------------------
    c.execute("""
    SELECT title, description, score FROM tasks WHERE user_id = 0 ORDER BY score DESC
    """)
    available_tasks = c.fetchall()
    displaying_available_tasks = []

    for i in available_tasks:
        displaying_available_tasks.append({
            "title": i[0],
            "description": i[1],
            "score": i[2]
        })

    # ------------ DISPLAY THE GROCERY LIST --------------------
    c.execute("""
    SELECT item_id, item from groceries
    """)
    results = c.fetchall()

    items = []

    for i in results:
        items.append({
            'item_id': i[0],
            'item':i[1]
        })

    # ------------ DISPLAY THE LIST OF IMPORTANT CONTACTS --------------------
    c.execute("""
    SELECT name, phone, email FROM contacts
    """)

    results = c.fetchall()

    contact_info = []

    for i in results:
        contact_info.append({
            'name': i[0],
            'phone': i[1],
            'email': i[2]
        })

    return render_template("index.html", user_reserved_tasks=user_reserved_tasks, items=items, user_completed_tasks=user_completed_tasks, displaying_available_tasks=displaying_available_tasks, contact_info=contact_info, scoreboard=scoreboard, display_reserved_gym=display_reserved_gym)

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

        flash("Task reserved! Please view your reserved tasks below.")

        return redirect("/")

# Complete Task: Users can complete a task and move it to a completed table for records of the week
@app.route("/complete/<reserve_id>", methods=["POST"])
@login_required
def complete_task(reserve_id):
    """ User will complete a task, remove it from reserved, and move to completed database """

    # Query the title and score of the completed task in reserved db
    c.execute("""
    SELECT title, score FROM reserved WHERE reserve_id = :reserve_id
    """, {"reserve_id": reserve_id})

    completed_task = c.fetchall()[0]

    title = completed_task[0]
    score = completed_task[1]
    
    c.execute("""
    DELETE FROM reserved WHERE reserve_id = :reserve_id
    """, {"reserve_id": reserve_id})
    conn.commit()

    c.execute("""
    INSERT INTO completed_tasks (user_id, title, score) VALUES (:user_id, :title, :score)
    """, {"user_id": session["user_id"], "title": title, "score": score})
    conn.commit()

    return redirect("/")

# If a user changes their mind on a task, they have the option to remove it
@app.route("/remove_task/<reserve_id>", methods=["POST"])
@login_required
def remove_task(reserve_id):
    """ User removes the task from their reserved list """

    # Query the tasks title
    c.execute("""
    SELECT title FROM reserved WHERE reserve_id = :reserve_id
    """, {"reserve_id": reserve_id})

    title = c.fetchall()[0][0]

    # Delete the task in the reserved db using reserve_id
    c.execute("""
    DELETE FROM reserved WHERE reserve_id = :reserve_id
    """, {"reserve_id": reserve_id})
    conn.commit()

    # Change the user_id in the tasks db back to 0 since it is no longer reserved
    c.execute("""
    UPDATE tasks SET user_id = 0 WHERE title = :title AND user_id = :user_id
    """, {"title": title, "user_id": session["user_id"]})

    flash("Task successfully removed from your list!")

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
        flash("New Task successfully created. It is viewable and reservable under 'Reserve'. ")

        return redirect("/")

# (COMPLETED) Edit: Users can select and edit a task
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

        flash("Task successfully edited!")

        return redirect("/")

# (COMPLETED) Delete: Users can delete tasks from the master list
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

        flash("Task successfully deleted!")

        return redirect("/")

# Gym: Users can reserve an amount of time to use the home gym
@app.route("/gym", methods=["GET", "POST"]) 
@login_required
def gym():
    # Users will be able to reserve gym time by selecting times and inputing dates

    if request.method == "GET":    
        gym_times = c.execute("""
        SELECT time, ampm FROM gym_times WHERE user_id = 0;
        """)

        return render_template("gym.html", times = [time[0] + time[1] for time in gym_times])

    else:
        # Synthesize the times above into a string format, and push into "gym_reserve" database under user_id
        start = request.form.get("start_times")
        end = request.form.get("end_times")

        # format looks like 12:00AM 1:00AM 2021-01-24
        # if the times are form PM to AM, we need to change user_id using gym_times_id and from end of database to start
        if start[len(start) - 2:] == 'PM' and end[len(end) - 2:] == 'AM':
            # start time in the pm
            search_start_time = start[:len(start) - 2]
            search_start_pm = start[len(start) - 2:]

            search_end_time = end[:len(end) - 2]
            search_end_am = end[len(end) - 2:]

            c.execute("""
            SELECT gym_id FROM gym_times WHERE time = :search_start_time AND ampm = :search_start_pm
            """, {"search_start_time": search_start_time, "search_start_pm": search_start_pm})

            reserving_pm = c.fetchall()[0][0]

            c.execute("""
            SELECT gym_id FROM gym_times WHERE time = :search_end_time AND ampm = :search_end_am
            """, {"search_end_time": search_end_time, "search_end_am": search_end_am})

            reserving_am = c.fetchall()[0][0]

            # All times between the PM to the AM time will set user_id to reserving user
            for i in range(reserving_pm, 49):
                c.execute("""
                UPDATE gym_times SET user_id = :user_id WHERE gym_id = :i
                """, {"user_id": session["user_id"], "i": i})
                conn.commit()

            # All times between 12:00am to the end time will set user_id to current user
            for i in range(1, reserving_am):
                c.execute("""
                UPDATE gym_times SET user_id = :user_id WHERE gym_id = :i
                """, {"user_id": session["user_id"], "i": i})
                conn.commit()
        else:
            # get the times of any reservation that is am-am, pm-pm, or am-pm
            search_start_time = start[:len(start) - 2]
            search_start_ampm = start[len(start) - 2:]
            search_end_time = end[:len(end) - 2]
            search_end_ampm = end[len(end) - 2:]

            # Query the gym_id of the selected start_time
            c.execute("""
            SELECT gym_id FROM gym_times WHERE time = :search_start_time AND ampm = :search_start_ampm
            """, {"search_start_time": search_start_time, "search_start_ampm": search_start_ampm})

            reserving_start = c.fetchall()[0][0]

            # Query the gym_id of the selected end_time
            c.execute("""
            SELECT gym_id FROM gym_times WHERE time = :search_end_time AND ampm = :search_end_ampm
            """, {"search_end_time": search_end_time, "search_end_ampm": search_end_ampm})

            reserving_end = c.fetchall()[0][0]

            # Change the user_id of gym_times for reservation
            for i in range(reserving_start, reserving_end):
                c.execute("""
                UPDATE gym_times SET user_id = :user_id WHERE gym_id = :i
                """, {"user_id": session["user_id"], "i": i})
                conn.commit()

        # Push the times into the homepage database
        c.execute("""
        INSERT INTO reserved_gym (user_id, start, end) VALUES (?, ?, ?)
        """, (session["user_id"], start, end))

        conn.commit()

        return redirect("/")

# Delete or complete a reserved gym time
@app.route("/delete_gym/<reserve_id>", methods=["POST"])
@login_required
def delete_gym(reserve_id):
    """ User confirms or deletes a reservation under the gym feature """

    c.execute("""
    DELETE FROM reserved_gym WHERE reserve_id = :reserve_id
    """, {"reserve_id": reserve_id})
    conn.commit()

    c.execute("""
    UPDATE gym_times SET user_id = 0 WHERE user_id = :user_id
    """, {"user_id": session["user_id"]})

    conn.commit()

    return redirect("/")

# Add grocery item
@app.route("/add_grocery", methods=["GET", "POST"])
@login_required
def add_grocery():
    """ Users can add grocery item(s) to the grocery list for all housemates to see """

    if request.method == "GET":
        return render_template("add_grocery.html")
    
    else:
        item_to_add = request.form.get("add_item")

        c.execute("""
        INSERT INTO groceries (user_id, item) VALUES (:user_id, :item_to_add)
        """, {"user_id": session["user_id"], "item_to_add": item_to_add})
        conn.commit()

        return redirect("/")

# Delete grocery item
@app.route("/delete/<item_id>", methods=['POST'])
@login_required
def delete_grocery(item_id):
    """ User is able to delete a grocery item via button """
    
    c.execute("""
    DELETE FROM groceries WHERE item_id = :item_id
    """, {"item_id": item_id})

    conn.commit()

    return redirect("/")

# Reset Option: tasks, gym
@app.route("/reset", methods=["GET", "POST"])
@login_required
def reset_():
    """ Users are able to reset the reserved tasks list where everyone will now have no tasks reserved """
    if request.method == "GET":
        flash("Caution: This action will reset for ALL!")
        return render_template("reset.html")
    else:
        # if both submissions are Yes, then clear the reserved task list, and set all tasks in database to user_id = 0
        if request.form.get("choose_reset") == "Tasks":
            c.execute("""
            DELETE FROM reserved
            """)
            conn.commit()

            c.execute("""
            DELETE FROM completed_tasks
            """)
            conn.commit()
        
            c.execute("""
            UPDATE tasks SET user_id = 0 WHERE user_id != 0
            """)
            conn.commit()
        
            flash("Tasks successfully reset!")

            return redirect("/")
        else:
            c.execute("""
            UPDATE gym_times SET user_id = 0 WHERE user_id != 0
            """)
            conn.commit()

            c.execute("""
            DELETE FROM reserved_gym
            """)
            conn.commit()

            flash("Gym times successfully reset!")

            return redirect("/")

# Reset tasks
@app.route("/reset_tasks", methods=["GET", "POST"])
@login_required
def reset_tasks():
    """ Users are able to reset the reserved tasks list where everyone will now have no tasks reserved """
    if request.method == "GET":
        return render_template("reset_tasks.html")
    else:
        # if both submissions are Yes, then clear the reserved task list, and set all tasks in database to user_id = 0
        if request.form.get("confirm_sunday") == "Yes" and request.form.get("all_complete") == "Yes":

            c.execute("""
            DELETE FROM reserved
            """)
            conn.commit()

            c.execute("""
            DELETE FROM completed_tasks
            """)
            conn.commit()
        
            c.execute("""
            UPDATE tasks SET user_id = 0 WHERE user_id != 0
            """)
            conn.commit()
        
            flash("Tasks successfully reset!")

            return redirect("/")
        else:
            flash("Please ensure it is 1) Sunday and 2) all housemates have completed their tasks.")
            return redirect("/reset")

# Logout Function
@app.route("/logout")
def logout():
    """ User's option to logout of the app """

    session.clear()
    return redirect("/login")