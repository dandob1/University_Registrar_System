#START ADS
from flask import Flask, session, render_template, redirect, url_for, request, flash, jsonify, abort
import sqlite3, re
from flask import Flask, render_template, request, session, redirect, url_for, flash
import sqlite3
import random
import re

app = Flask('app')
app.secret_key = "poop fart"
app.debug = True

def get_db_connection(): #basic getting connection fucntion to avoid repetitivness 
    conn = sqlite3.connect('phase-2.db')
    conn.row_factory = sqlite3.Row
    return conn

#home route
@app.route('/home', methods=['GET'])
def home():
    if 'uid' in session:
        uid = session['uid']
        connection = sqlite3.connect("phase-2.db")
        connection.row_factory = sqlite3.Row
        cur = connection.cursor()

        #fetch user from db
        cur.execute("SELECT uid, email, username, password, user_type, first_name AS fname, last_name AS lname, address FROM users WHERE uid = ?", (uid,))

        user = cur.fetchone()
        session['user_type'] = user['user_type']
        #redirect to the correct page for the user type.
        if user:
            #grad student
            if user["user_type"] == 2:
                cur.execute("SELECT g.*, g.form1_submitted AS form_submitted, g.form1_approved  AS form_approved FROM grad_student g WHERE g.uid = ?", (uid,))
                student = cur.fetchone()
                connection.commit()
                suss = False

                cur.execute("""SELECT C.course_title AS course_name, d.d_name AS dept, C.crn AS course_number, C.credits, T.semester, T.grade 
                    FROM transcript T
                    JOIN courses C ON T.crn = C.crn
                    JOIN department d ON C.d_num = d.d_num
                    WHERE T.student_uid = ?
                    ORDER BY T.semester""", (uid,))
                coursesTaken = cur.fetchall()
                connection.commit()

                cur.execute(""" SELECT C.course_title AS course_name, d.d_name AS dept, C.crn AS course_number, C.credits FROM form_courses FC 
                    JOIN courses C ON FC.crn = C.crn JOIN department d ON C.d_num = d.d_num
                    LEFT JOIN transcript T ON T.student_uid = FC.student_uid AND T.crn = C.crn WHERE FC.student_uid = ? AND T.crn IS NULL""", (uid,))
                coursesPlan = cur.fetchall()
                connection.commit()

                #letter count for suspension
                cur.execute("SELECT COUNT(grade) FROM transcript WHERE student_uid = ? AND grade IN ('B-','C+','C','C-','F')", (uid,))
                sussCount = cur.fetchone()[0]
                connection.commit()

                if sussCount > 3:
                    cur.execute("UPDATE grad_student SET is_suspended = 1 WHERE uid = ?", (uid,))
                    connection.commit()
                    suss = True
                else:
                    cur.execute("UPDATE grad_student SET is_suspended = 0 WHERE uid = ?", (uid,))
                    connection.commit()
                    suss = False
                connection.close()

                return render_template("studentHome.html", user=user, student = student, coursesTaken = coursesTaken, coursesPlan = coursesPlan, suss = suss)
            #faculty advisor
            elif user["user_type"] == 3:
                cur.execute("""SELECT u.first_name AS fname, u.last_name AS lname, g.program, g.uid, g.form1_submitted AS form_submitted, g.form1_approved  AS form_approved, g.thesis_submitted, g.thesis_approved,
                            t.title AS thesis_title, t.abstract AS thesis_abstract FROM users u
                            JOIN grad_student g ON u.uid = g.uid
                            LEFT JOIN thesis t  ON t.student_uid = g.uid
                            WHERE g.advisor_uid = ?""", (uid,))
                students = cur.fetchall()
                print(students)
                connection.close()
                session['role'] = get_faculty_role(user['uid'])
                return render_template("faHome.html", user=user, students=students)
            #grad secretary
                cur.execute("""SELECT u.first_name AS fname, u.last_name AS lname, g.program, g.uid, g.form1_submitted AS form_submitted, g.form1_approved  AS form_approved, g.thesis_submitted, g.thesis_approved,
                            t.title AS thesis_title, t.abstract AS thesis_abstract FROM users u
                            JOIN grad_student g ON u.uid = g.uid
                            LEFT JOIN thesis t  ON t.student_uid = g.uid
                            WHERE g.advisor_uid = ?""", (uid,))
                students = cur.fetchall()
                print(students)
                connection.close()
                return render_template("faHome.html", user=user, students=students)
            #grad secretary
            elif user["user_type"] == 5:
                program = request.args.get('program', '').strip()
                year    = request.args.get('admit_year', '').strip()
                query   = request.args.get('query', '').strip()

                base = """
                    SELECT
                    u.uid,
                    u.first_name AS fname,
                    u.last_name  AS lname,
                    g.program,
                    g.gpa,
                    g.advisor_uid,
                    g.graduation_requested AS grad_requested
                    FROM users u
                    JOIN grad_student g ON u.uid = g.uid
                """
                filters = []
                params  = []
                if program:
                    filters.append("g.program LIKE ?")
                    params.append(f"%{program}%")
                if year:
                    filters.append("strftime('%Y', g.matriculation_date) = ?")
                    params.append(year)
                if query:
                    filters.append("(u.first_name LIKE ? OR u.last_name LIKE ? OR u.uid LIKE ?)")
                    params += [f"%{query}%", f"%{query}%", f"%{query}%"]
                if filters:
                    base += " WHERE " + " AND ".join(filters)

                cur.execute(base, params)
                students = cur.fetchall()

                # Fetch advisors
                cur.execute("SELECT u.uid, u.first_name AS fname, u.last_name AS lname FROM users u JOIN faculty f ON f.uid = u.uid WHERE f.is_advisor = 1")
                advisors = cur.fetchall()

                assignedAdvisor = {}
                for advisor in advisors:
                    uid = advisor['uid']
                    name = advisor['fname'] + " " + advisor['lname']
                    assignedAdvisor[uid] = name
                
                connection.close()
                session['role'] = "gs"
                return render_template("gsHome.html",
                              user=user,
                              students=students,
                              advisors=advisors,
                              assignedAdvisor=assignedAdvisor,
                              program=program,
                              year=year,
                              query=query)
            #system admin
            elif user["user_type"] == 4:
                cur.execute("SELECT uid, email, username, user_type, first_name AS fname, last_name AS lname, address FROM users")
                allUsers = cur.fetchall()
                connection.close()
                session['role'] = "admin"
                return render_template("REGS-admin.html") 
            #alumni
            elif user["user_type"] == 6:
                cur.execute("SELECT u.*, a.graduation_semester AS semYear, a.degree AS Degree FROM users u JOIN alumni a ON u.uid = a.uid WHERE u.uid = ?", (uid,))
                students = cur.fetchone()
                connection.close()
                cumulativeGPA = calculateGPA(uid)
                return render_template("alumHome.html", user=user, students = students, cumulativeGPA = cumulativeGPA) 
            #applicant
            elif user["user_type"] == 1:
                user = connection.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone()
                applicant = connection.execute("SELECT * FROM applicant WHERE uid = ?", (uid,)).fetchone()
                connection.close()
                if user and applicant:
                    session['role'] = 'applicant'
                    return redirect(url_for('applicant_dashboard'))
                else:
                    return redirect(url_for('login'), error = 'Invalid UID or password. Please try again.')
            
    return redirect("/")  #redirect to login page if not logged in

#login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST': 
        input = request.form["uid"]
        pw = request.form["password"]

        #check if input is an email or uid
        if '@' in input:
            #fetch user from db
            connection = sqlite3.connect("phase-2.db")
            connection.row_factory = sqlite3.Row
            cur = connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (input, pw))
            user = cur.fetchone()
            if not user:
                return render_template("login.html", error="Invalid username or password.")
            uid = user["uid"]
        else:
            uid = input
            connection = sqlite3.connect("phase-2.db")
            connection.row_factory = sqlite3.Row
            cur = connection.cursor()
            #fetch user from db
            cur.execute("SELECT * FROM users WHERE uid = ? AND password = ?", (uid, pw))
            user = cur.fetchone()

        if user:
            session['uid'] = uid
            session['name'] = f"{user['first_name']} {user['last_name']}"
            session['email'] = user['email']
            connection.close()
            return redirect("/home")  #redirect to home page upon successful login
        else:
            connection.close()
            return render_template("login.html", error="Invalid username or password.")  #pass error message

    return render_template("login.html")

#signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        password = request.form['password']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        address = request.form['address']
        program = request.form.get('program')

        connection = sqlite3.connect("phase-2.db")
        cur = connection.cursor()

        # Check if email is already registered
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cur.fetchone()

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template("signup.html", error = "Please enter a valid email address")

        if existing_user:
            connection.close()
            return render_template("signup.html", error = "Email is already registered")

        # Insert new user if email is not registered
        cur.execute("INSERT INTO users (user_type, password, fname, lname, email, address) VALUES (?, ?, ?, ?, ?, ?)",
                    ('grad_student', password, firstName, lastName, email, address))
        connection.commit()

        uid = cur.lastrowid  # Get the last inserted row ID

        if program not in ["MS", "PhD"]:
            program = "MS"

        cur.execute("INSERT INTO grad_student (uid, credit_hours, advisor_UID, gpa, dept, program, is_suspended, form_submitted) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, 0, None, 0.0, 'Computer Science', program, 0, 0))
        connection.commit()
        connection.close()

        return render_template("login.html", success="Account created successfully! Please log in.")
    return render_template("signup.html")

#SA signup
@app.route('/sasignup', methods=['GET', 'POST'])
def sasignup():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT user_type FROM users WHERE uid = ?", (session['uid'],))
    user_type = cur.fetchone()

    if not user_type or user_type['user_type'] != 4:
        connection.close()
        return redirect(url_for('home'))  # Redirect to home if not a system admin
    connection.close()
    
    if request.method == 'POST':
        userType = request.form.get('userType', '')
        uid = request.form['uid']
        password = request.form['password']
        username = request.form['username']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        address = request.form['address']

        connection = sqlite3.connect("phase-2.db")
        cur = connection.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cur.fetchone()

        cur.execute("SELECT * FROM users WHERE uid = ?", (uid,))
        existing_uid = cur.fetchone()

        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_username = cur.fetchone()

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template("saHome.html", error = "Please enter a valid email address")
        
        if not re.match(r'^\d{8}$', uid):
            return render_template("saHome.html", error = "Please enter a 8 digit uid")

        if existing_user:
            connection.close()
            return render_template("saHome.html", error = "Email is already registered")
        
        if existing_uid:
            connection.close()
            return render_template("saHome.html", error = "UID is already registered")
        
        if existing_username:
            connection.close()
            return render_template("saHome.html", error = "Username is already registered")

        cur.execute("INSERT INTO users (uid, user_type, password, username, first_name, last_name, email, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, userType, password, username, firstName, lastName, email, address))
        connection.commit()
        
        uid = cur.lastrowid
        if userType == "2":
            program = request.form.get('program', 'MS in Computer Science')
            if program not in ["MS in Computer Science", "PhD in Computer Science"]:
                program = "MS in Computer Science"
            cur.execute("INSERT INTO grad_student (uid, credit_hours, advisor_UID, gpa, d_num, program, is_suspended, form1_submitted, matriculation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (uid, 0, None, 0.0, 1, program, 0, 0, 2024-10-15))
            connection.commit()
        elif userType == "3":
            dept = request.form.get('dept', 1)
            cur.execute("INSERT INTO faculty (uid, d_num) VALUES (?, ?)", (uid, dept))
            connection.commit()
        elif userType == "4":
            cur.execute("INSERT INTO systems_admin (uid) VALUES (?)", (uid,))
            connection.commit()
        elif userType == "5":
            cur.execute("INSERT INTO grad_secretary (uid) VALUES (?)", (uid,))
            connection.commit()
        elif userType == "6":
            semYear = request.form.get('semYear', '')
            degree  = request.form.get('degree', '')
            cur.execute("INSERT INTO alumni (uid, graduation_semester, Degree) VALUES (?, ?, ?)", (uid, semYear, degree))
            connection.commit()

        connection.commit()
        connection.close()

        return redirect(url_for('sasignup'))
    #repopulate the table
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT uid, first_name AS fname, last_name AS lname, username, email, address, user_type FROM users")
    allUsers = cur.fetchall()
    connection.close()
    return render_template("saHome.html", allUsers=allUsers)

#logout
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for("login"))

#Grad Secretary Search
@app.route('/search', methods=['GET'])
def search():
    if 'uid' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '').strip()
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("""SELECT u.uid, u.first_name AS fname, u.last_name AS lname, g.program, g.gpa, g.advisor_uid, g.graduation_requested AS grad_requested
    FROM users AS u 
    JOIN grad_student AS g ON u.uid = g.uid 
    WHERE u.first_name LIKE ? OR u.last_name LIKE ? OR u.uid LIKE ?
    """, ('%' + query + '%', '%' + query + '%', '%' + query + '%'))
    students = cur.fetchall()

    # Fetch advisor names
    cur.execute("SELECT u.uid, u.first_name, u.last_name FROM users AS u JOIN faculty AS f ON u.uid = f.uid WHERE f.is_advisor = 1")
    advisors = {row['uid']: f"{row['first_name']} {row['last_name']}" for row in cur.fetchall()}

    connection.close()

    # Add advisor names to students
    student_list = [
        {
            'uid': student['uid'],
            'fname': student['fname'],
            'lname': student['lname'],
            'program': student['program'],
            'gpa': student['gpa'],
            'advisor_uid': student['advisor_uid'],
            'advisorName': advisors.get(student['advisor_uid'], 'Not Assigned'),
            'grad_requested': bool(student['grad_requested'])
        }
        for student in students
    ]
    return jsonify(student_list)

# Faculty Advisor Search
@app.route('/searchMyStudents', methods=['GET'])
def searchMyStudents():
    if 'uid' not in session:
        return jsonify([])

    advisor_uid = session['uid']
    query = request.args.get('query', '').strip()

    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    cur.execute("""
        SELECT u.uid, u.first_name AS fname, u.last_name AS lname, g.program, g.form1_submitted, g.form1_approved
        FROM users u
        JOIN grad_student g ON u.uid = g.uid
        WHERE g.advisor_uid = ?
          AND (u.first_name LIKE ? OR u.last_name LIKE ? OR u.uid LIKE ?)
    """, (advisor_uid, f"%{query}%", f"%{query}%", f"%{query}%"))

    students = cur.fetchall()
    connection.close()

    return jsonify([
        {
            'uid': s['uid'],
            'fname': s['fname'],
            'lname': s['lname'],
            'program': s['program'],
            'form_submitted': s['form1_submitted'],
            'form_approved': s['form1_approved'],
        }
        for s in students
    ])

#system admin search
@app.route('/searchUsers', methods=['GET'])
def searchUsers():
    if 'uid' not in session:
        return jsonify([])  # Return an empty list if the user is not logged in

    query = request.args.get('query', '').strip()  # Get the search query
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    try:
        cur.execute("""
            SELECT * FROM users 
            WHERE uid LIKE ? OR fname LIKE ? OR lname LIKE ? OR email LIKE ? OR address LIKE ?
        """, ('%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%'))
        users = cur.fetchall()
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify([])  # Return an empty list on error
    finally:
        connection.close()

    user_list = [
        {
            'uid': user['uid'],
            'fname': user['fname'],
            'lname': user['lname'],
            'user_type': user['user_type'],
            'email': user['email'],
            'address': user['address']
        }
        for user in users
    ]
    return jsonify(user_list)

@app.route('/searchAdvisors', methods=['GET'])
def searchAdvisors():
    if 'uid' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '')
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    # Search advisors based on query
    cur.execute("""
        SELECT uid, fname, lname 
        FROM users 
        WHERE user_type = 'faculty_advisor' 
        AND (fname LIKE ? OR lname LIKE ? OR uid LIKE ?)
    """, ('%' + query + '%', '%' + query + '%', '%' + query + '%'))
    advisors = cur.fetchall()
    connection.close()

    # Convert to list of dicts for JSON response
    advisor_list = [{'uid': a['uid'], 'fname': a['fname'], 'lname': a['lname']} for a in advisors]
    return jsonify(advisor_list)

@app.route('/editInfo', methods=['GET', 'POST'])
def editInfo():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    uid = session['uid']  

    if request.method == 'POST':
        # update user information in the database
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        address = request.form['address']

        connection = sqlite3.connect("phase-2.db")
        cur = connection.cursor()
        cur.execute("UPDATE users SET first_name=?, last_name=?, email=?, address=? WHERE uid=?", 
                    (firstName, lastName, email, address, uid))
        connection.commit()
        connection.close()

        return render_template("editInfo.html", success = "Information updated successfully!", user_info={'fname': firstName, 'lname': lastName, 'email': email, 'address': address}, success_message="Information updated successfully!")
        # return redirect(url_for('home'))

    # fetch current user information to pre-fill the form
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT first_name AS fname, last_name AS lname, email, address FROM users WHERE uid=?", (uid,))
    user_info = cur.fetchone()
    connection.close()

    return render_template("editInfo.html", user_info=user_info)

#edit info of a different user
@app.route('/editUser/<int:uid>', methods=['GET', 'POST'])
def editUser(uid):
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT user_type FROM users WHERE uid = ?", (session['uid'],))
    user_type = cur.fetchone()

    if not user_type or user_type['user_type'] not in (4, 5):
        connection.close()
        return redirect(url_for('home'))  # Redirect to home if not a system admin
    connection.close()
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    if request.method == 'POST':
        # update user information in the database
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        address = request.form['address']
        # Check if current user is a GS (user_type == 5)
        if user_type['user_type'] == 5:
            # GS should NOT update password
            cur.execute("""
                UPDATE users 
                SET first_name = ?, last_name = ?, email = ?, address = ?
                WHERE uid = ?
            """, (firstName, lastName, email, address, uid))
        else:
            # Admin can update password
            password = request.form['password']
            cur.execute("""
                UPDATE users 
                SET first_name = ?, last_name = ?, email = ?, address = ?, password = ?
                WHERE uid = ?
            """, (firstName, lastName, email, address, password, uid))

        connection.commit()
        connection.close()

        return redirect(url_for('home'))
    
    cur.execute("SELECT * FROM users WHERE uid=?", (uid,))
    user_info = cur.fetchone()
    connection.close()

    return render_template("editUser.html", user_info=user_info)
    
#delete user
@app.route('/deleteUser/<int:uid>', methods=['POST'])
def deleteUser(uid):
    connection = sqlite3.connect("phase-2.db")
    cur = connection.cursor()

    cur.execute("DELETE FROM users WHERE uid = ?", (uid,))
    connection.commit()
    connection.close()
    return redirect(url_for('home'))

#Transcript route
@app.route('/transcript/<int:uid>', methods=['GET'])
def transcript(uid):
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    logged_in_uid = session['uid']
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    # Fetch the logged-in user's role
    cur.execute("SELECT user_type FROM users WHERE uid = ?", (logged_in_uid,))
    user = cur.fetchone()
    if not user:
        connection.close()
        return redirect(url_for('login'))  # Redirect if user not found

    role = user['user_type']
    if role == 2:
        is_student = True
    else:
        is_student = False

    if role == 6:
        is_alumni = True
    else:
        is_alumni = False

    if role == 3:
        is_faculty = True
    else:
        is_faculty = False

    # Check access permissions
    if (is_student or is_alumni) and str(logged_in_uid) != str(uid):
        connection.close()
        return redirect(url_for('home'))


    if is_faculty:
        # Verify the student is assigned to the faculty advisor
        cur.execute("SELECT * FROM grad_student WHERE uid = ? AND advisor_uid = ?", (uid, logged_in_uid))
        student = cur.fetchone()
        if not student:
            connection.close()
            return redirect(url_for('home'))  # Redirect if the student is not assigned to the advisor

    cur.execute("""SELECT t.semester, c.course_title AS course_name, c.crn AS course_number, d.d_name AS dept,c.credits, t.grade FROM transcript t JOIN courses c ON t.crn  = c.crn 
                JOIN department d ON c.d_num = d.d_num
                WHERE t.student_uid = ? 
                ORDER BY t.semester""",(uid,))
    transcript = cur.fetchall()
    cumulativeGPA = calculateGPA(uid)

    if cumulativeGPA is not None:
        cur.execute("UPDATE grad_student SET gpa = ? WHERE uid = ?", (cumulativeGPA, uid))
        connection.commit()
    else:
        cur.execute("UPDATE grad_student SET gpa = 0.00 WHERE uid = ?", (uid,))
        connection.commit()

    cur.execute("SELECT first_name AS fname, last_name AS lname FROM users WHERE uid = ?", (uid,))
    student = cur.fetchone()
    if student:
        studentName = student['fname'] + " " + student['lname']
    else:
        studentName = "WHO IS THIS STUDENT"

    cur.execute("SELECT advisor_uid FROM grad_student WHERE uid = ?", (uid,))
    advisor_row = cur.fetchone()
    display = "N/A"
    if advisor_row is not None:
        advisorUID = advisor_row["advisor_UID"]
        if advisorUID:
            cur.execute("SELECT first_name AS fname, last_name AS lname FROM users WHERE uid = ?", (advisorUID,))
            advisorName = cur.fetchone()
            if advisorName:
                display = advisorName['fname'] + " " + advisorName['lname']
    else:
        advisorUID = None
    
    connection.close()

    return render_template("transcript.html",  uid= session['uid'], transcript = transcript, cumulativeGPA = cumulativeGPA, studentName=studentName, display=display)

#calculate the GPA
def calculateGPA(uid):
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT C.credits, T.grade FROM transcript T JOIN courses C ON T.crn = C.crn WHERE T.student_uid = ?",(uid,))
    transcript = cur.fetchall()
    connection.close()

    if not transcript:
        return None
    points = 0
    totalCredits = 0
    calculations = {'A': 4.0, 'A-': 3.7, 'B+': 3.4, 'B': 3.0, 'B-': 2.7, 'C+': 2.4, 'C': 2.0, 'C-': 1.7, 'D+': 1.4, 'D': 1.0, 'D-': 0.4, 'F': 0.0}
    for classes in transcript:
        grade = classes['grade']
        credits = classes['credits']
        if grade in calculations:
            points += calculations[grade] * credits
            totalCredits += credits
    
    if totalCredits == 0:
        return None
    return round(points / totalCredits, 2)

#Form route
@app.route('/form', methods=['GET', 'POST'])
def form():
    #Make sure student is logged in
    if 'uid' not in session:
        return redirect('/login')  # Just in case

    uid = session['uid']
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()    

    cur.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cur.fetchone()
    connection.commit()

    cur.execute(""" SELECT d.d_name AS dept, C.crn AS course_id, C.credits, C.course_title AS course_name,
                        d1.d_name || ' ' || PR1.crn     AS prereq1,
                        d2.d_name || ' ' || PR2.crn     AS prereq2
                    FROM courses C
                    JOIN department d ON C.d_num = d.d_num
                    LEFT JOIN prerequisite P1 ON C.crn = P1.course_id
                    LEFT JOIN courses PR1 ON P1.prereq_id = PR1.crn
                    LEFT JOIN department d1 ON PR1.d_num = d1.d_num
                    LEFT JOIN prerequisite P2 ON C.crn = P2.course_id AND P2.prereq_id > P1.prereq_id
                    LEFT JOIN courses PR2 ON P2.prereq_id = PR2.crn
                    LEFT JOIN department d2 ON PR2.d_num = d2.d_num
                    GROUP BY C.crn;""")
    courses = cur.fetchall()
    connection.commit()

    cur.execute("SELECT * FROM grad_student WHERE uid = ?", (uid,))
    student = cur.fetchone()
    connection.commit()

    cur.execute("SELECT form1_submitted FROM grad_student WHERE uid = ?", (uid,))
    form_submitted = cur.fetchone()[0]
    connection.commit()
    if form_submitted == 1:
        connection.close()
        return redirect(url_for('viewForm', Fuid=uid, success="You have already submitted a form."))
    
    cur.execute("SELECT crn AS course_id FROM transcript WHERE student_uid = ?", (uid,))
    coursesTaken =[row['course_id'] for row in cur.fetchall()]
    connection.commit()

    if request.method == 'POST':

        deleteCourses = """DELETE FROM form_courses
                        WHERE student_uid = ?"""
        cur.execute(deleteCourses, (uid,))
        connection.commit()

        cur.execute("SELECT program FROM grad_student WHERE uid = ?", (uid,))
        program = cur.fetchone()[0]
        connection.commit()

        selectedCourses = request.form.getlist('courses')

        for course_id in set(selectedCourses):
            cur.execute("INSERT INTO form_courses (student_uid, crn) VALUES (?, ?)", (uid, course_id))
            connection.commit()

        # Check that pre-requisites are met
        query = """SELECT FC.student_uid, FC.crn AS course_id, PR.prereq_id FROM form_courses FC
                JOIN prerequisite PR ON FC.crn = PR.course_id
                LEFT JOIN form_courses FC2 ON FC.student_uid = FC2.student_uid AND PR.prereq_id = FC2.crn
                WHERE FC.student_uid = ? AND FC2.crn IS NULL"""
        cur.execute(query, (uid,))
        preReqs = cur.fetchall()

        if preReqs:
            return render_template('form.html', error = "You do not have the required pre-requisites.", user = user, courses = courses, student = student, coursesTaken = coursesTaken)
        
        if program == "PhD in Computer Science":
            #Check 36 Credits
            query = """ SELECT SUM(credits) FROM courses
                        JOIN form_courses FC ON courses.crn = FC.crn
                        WHERE FC.student_uid = ? """
            cur.execute(query, (uid,))
            credits = cur.fetchone()
            totalCredits = credits[0]
            if totalCredits is None:
                totalCredits = 0
                
            if totalCredits < 36:
                return render_template('form.html', error = "You do not have enough credits.", user = user, courses = courses, student = student, coursesTaken = coursesTaken)
            
            #Check 30 CSCI Credits
            query = """ SELECT SUM(credits) FROM courses c
                        JOIN department d ON c.d_num = d.d_num
                        JOIN form_courses fc ON c.crn = fc.crn 
                        WHERE fc.student_uid = ? AND d.d_name = 'CSCI'"""
            cur.execute(query, (uid,))
            csciCredits = cur.fetchone()
            totalCSCI = csciCredits[0]
            if totalCSCI < 30:
                return render_template('form.html', error = "You do not have enough CSCI credits.", user = user, courses = courses, student = student, coursesTaken = coursesTaken)
        elif program == "MS in Computer Science":
            #Check The Student has course ID's: 1, 2, 3 selected
            query = """ SELECT COUNT(*) FROM form_courses FC
                        WHERE FC.student_uid = ? AND FC.crn IN (6221, 6461, 6212) 
                        """
            cur.execute(query, (uid,))
            count = cur.fetchone()
            totalCount = count[0]
            if totalCount < 3:
                return render_template('form.html', error = "You do not have the required courses", user = user, courses = courses, student = student, coursesTaken = coursesTaken)

            #Check 30 Credits
            query = """ SELECT SUM(credits) FROM courses
            JOIN form_courses FC ON courses.crn = FC.crn
            WHERE FC.student_uid = ? """
            cur.execute(query, (uid,))
            credits = cur.fetchone()
            totalCredits = credits[0]
            if totalCredits < 30:
                return render_template('form.html', error = "You do not have enough credits.", user = user, courses = courses, student = student, coursesTaken  = coursesTaken)   
            #Check at most 2 Clases outside of CS Department
            query = """ SELECT COUNT(*) FROM courses c
                        JOIN department d ON c.d_num = d.d_num
                        JOIN form_courses fc ON c.crn = fc.crn
                        WHERE fc.student_uid = ? AND d.d_name != 'CSCI'"""
            cur.execute(query, (uid,))
            nonCSClasses = cur.fetchone()
            totalNonCS = nonCSClasses[0]
            if totalNonCS > 2:
                return render_template('form.html', error = "You have too many classes outside of the CS department.",  user = user, courses = courses, student = student, coursesTaken = coursesTaken)
        else:
            return render_template('form.html', error = "Invalid program selected.", user = user, courses = courses, student = student, coursesTaken = coursesTaken)

        cur.execute("UPDATE grad_student SET form1_submitted = ? WHERE uid = ?", (1, uid))
        connection.commit()

        connection.close()  # Ensure the connection is closed after committing
        return redirect(url_for('viewForm', Fuid=student['uid'], success="Form submitted successfully!"))

    connection.close()
    return render_template('form.html', user = user, courses = courses, student = student, coursesTaken = coursesTaken)

@app.route('/viewForm/<int:Fuid>/', defaults={'success': None}, methods=['GET', 'POST'])
@app.route('/viewForm/<int:Fuid>/<string:success>', methods=['GET', 'POST'])
def viewForm(Fuid, success):

    if 'uid' not in session:
        return redirect('/login')
    
    uid = session['uid']
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    if request.method == 'POST':
        form_status = request.form.get("status")
        if form_status == 'approve':
            cur.execute("UPDATE grad_student SET form1_approved = 1, has_advising_hold = 0 WHERE uid = ?", (Fuid,))
            connection.commit()
            success = "Form approved successfully!"
        elif form_status == 'reject':
            cur.execute("UPDATE grad_student SET form1_submitted = 0 WHERE uid = ?", (Fuid,))
            connection.commit()

            cur.execute("DELETE FROM form_courses WHERE student_uid = ?", (Fuid,))
            connection.commit()

            success = "Form denied successfully!"

            return redirect (url_for('home'))


    cur.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cur.fetchone()

    cur.execute("""SELECT g.*, u.first_name AS fname, u.last_name AS lname, u.user_type, u.email, u.address FROM grad_student g JOIN users u ON g.uid = u.uid WHERE g.uid = ?""", (Fuid,))    
    student = cur.fetchone()


    query = """SELECT d.d_name AS dept, C.crn AS course_id, C.credits, C.course_title AS course_name,
        CASE WHEN FC.crn IS NOT NULL THEN 'True' ELSE 'False' END AS selected
        FROM courses C JOIN department d ON C.d_num = d.d_num
        LEFT JOIN form_courses FC ON C.crn = FC.crn AND FC.student_uid = ?"""

    cur.execute(query, (Fuid,))
    courseSelect = cur.fetchall()

    connection.close()

    return render_template('viewForm.html', success=success, user=user, student=student, courseSelect=courseSelect)

@app.route('/assignAdvisor', methods=['POST'])
def assignAdvisor():

    data = request.get_json()
    student_uid = data.get('studentUid')
    advisor_uid = data.get('advisorUid')

    if not student_uid or not advisor_uid:
        return jsonify({'error': 'Invalid data'}), 400

    connection = sqlite3.connect("phase-2.db")
    cur = connection.cursor()
    cur.execute("UPDATE grad_student SET advisor_UID = ? WHERE uid = ?", (advisor_uid, student_uid))
    connection.commit()
    connection.close()

    return jsonify({'success': True}), 200

@app.route('/getAdvisors', methods=['GET'])
def getAdvisors():
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    cur.execute("SELECT uid, fname, lname FROM users WHERE user_type = 'faculty_advisor'")
    advisors = cur.fetchall()
    connection.close()

    # Convert to list of dicts
    advisor_list = [{'uid': a['uid'], 'fname': a['fname'], 'lname': a['lname']} for a in advisors]
    return jsonify(advisor_list)

@app.route('/gradRequested', methods=['POST'])
def gradRequested():
    if 'uid' not in session:
        return render_template("login.html", error="You must log in to request graduation.")
    uid = session['uid']

    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    cur.execute("""
        SELECT
        uid,
        email,
        username,
        password,
        user_type,
        first_name AS fname,
        last_name  AS lname,
        address
        FROM users
        WHERE uid = ?
    """, (uid,))
    user = cur.fetchone()

    cur.execute("SELECT * FROM grad_student WHERE uid = ?", (uid,))
    student = cur.fetchone()

    cur.execute("""SELECT C.course_title AS course_name, d.d_name AS dept, C.crn AS course_number, C.credits, T.semester, T.grade
                FROM transcript T
                JOIN courses C ON T.crn = C.crn
                JOIN department d ON C.d_num = d.d_num
                WHERE T.student_uid = ?
                ORDER BY T.semester""", (uid,))
    coursesTaken = cur.fetchall()

    cur.execute(""" SELECT C.course_title AS course_name, d.d_name AS dept, C.crn AS course_number, C.credits
                FROM form_courses FC
                JOIN courses      C ON FC.crn = C.crn
                JOIN department   d ON C.d_num = d.d_num
                LEFT JOIN transcript T ON FC.student_uid = T.student_uid AND FC.crn = T.crn
                WHERE FC.student_uid = ? AND T.crn IS NULL""", (uid,))
    coursesPlan = cur.fetchall()

    cur.execute("SELECT COUNT(grade) FROM transcript WHERE student_uid = ? AND grade IN ('B-','C+','C','C-','F')", (uid,))
    sussCount = cur.fetchone()[0]

    suss = False
    if student["program"] == "MS" and sussCount > 2:
        suss = True
    elif student["program"] == "PhD" and sussCount > 1:
        suss = True

    cur.execute("SELECT form1_submitted, graduation_requested FROM grad_student WHERE uid = ?", (uid,))
    student_status = cur.fetchone()
    if not student_status:
        connection.close()
        return render_template("studentHome.html", user=user, student=student, coursesTaken=coursesTaken, coursesPlan=coursesPlan, suss=suss, error="No student record found.")
    
    if student_status['form1_submitted'] == 0:
        connection.close()
        return render_template("studentHome.html", user=user, student=student, coursesTaken=coursesTaken, coursesPlan=coursesPlan, suss=suss, error="You must submit a form before requesting graduation.")
    
    if student_status['graduation_requested']:
        connection.close()
        return render_template("studentHome.html", user=user, student=student, coursesTaken=coursesTaken, coursesPlan=coursesPlan, suss=suss, error="Graduation request has already been submitted.")
    
    cur.execute("UPDATE grad_student SET graduation_requested = 1 WHERE uid = ?", (uid,))
    connection.commit()
    connection.close()

    return render_template("studentHome.html", user=user, student=student, coursesTaken=coursesTaken, coursesPlan=coursesPlan, suss=suss, success="Graduation request submitted successfully!")

#thesis logic
@app.route('/thesis', methods=['GET', 'POST'])
def thesis():
    if 'uid' not in session:
        return redirect(url_for('login'))

    uid = int(session['uid'])
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    
    #make sure its the right user
    cur.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cur.fetchone()
    cur.execute("SELECT program, thesis_submitted, thesis_approved, advisor_uid FROM grad_student WHERE uid = ?", (uid,))
    student = cur.fetchone()
    if not user or not student or user['user_type'] != 2:
        connection.close()
        return redirect(url_for('home'))
    #only phd students can submit a thesis
    if 'PhD' not in student['program']:
        connection.close()
        return render_template("thesis.html", error="Only PhD students can submit a thesis.", user=user, student=student)
    
    if request.method == 'POST':
        title    = request.form.get("title",   "").strip()
        thesis = request.form.get("thesis",  "").strip()
        advisor  = student['advisor_uid']
        
        if not title or not thesis:
            connection.close()
            return render_template("thesis.html", error="Both title and abstract are required.", user=user, student=student, thesis=thesis, thesis_title=title)
        
        #update the thesis or pull it from before
        cur.execute("SELECT 1 FROM thesis WHERE student_uid = ?", (uid,))
        oldThesis = cur.fetchone()
        if oldThesis:
            cur.execute("UPDATE thesis SET title = ?, abstract = ? WHERE student_uid = ?", (title, thesis, uid))
        else:
            cur.execute("INSERT INTO thesis (student_uid, title, abstract, advisor_uid, submission_date) VALUES (?, ?, ?, ?, date('now'))", (uid, title, thesis, advisor))

        #update that its submitted
        cur.execute("UPDATE grad_student SET thesis_submitted = 1, thesis_approved = 0 WHERE uid = ?", (uid,))
        connection.commit()
        connection.close()
        return render_template("thesis.html", success="Thesis submitted, advisor will analyze soon.", user=user, student=student, thesis=thesis, thesis_title=title)
    
    else:
        #get method
        cur.execute("SELECT abstract FROM thesis WHERE student_uid = ?", (uid,))
        row = cur.fetchone()
        if row:
            thesis = row['abstract']
        else:
            thesis = ""
        connection.close()
        return render_template("thesis.html", user=user, student=student, thesis=thesis)
    
@app.route('/viewThesis/<int:Fuid>', methods=['GET', 'POST'])
def viewThesis(Fuid):
    if 'uid' not in session:
        return redirect(url_for('login'))

    loggedin = int(session['uid'])
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    cur.execute("SELECT * FROM users WHERE uid = ?", (loggedin,))
    user = cur.fetchone()
    if not user or user['user_type'] != 3:
        connection.close()
        return redirect(url_for('home'))

    cur.execute("SELECT g.*, u.first_name AS fname, u.last_name  AS lname FROM grad_student g JOIN users u ON u.uid = g.uid WHERE g.uid = ? AND g.advisor_uid = ?", (Fuid, loggedin))
    student = cur.fetchone()
    if not student:
        connection.close()
        return redirect(url_for('home'))

    cur.execute("SELECT abstract FROM thesis WHERE student_uid = ?", (Fuid,))
    row = cur.fetchone()
    if row:
        thesis = row['abstract']
    else:
        thesis = ""

    if request.method == 'POST':
        action = request.form.get("action")
        if action == "approve":
            cur.execute("UPDATE grad_student SET thesis_approved = 1 WHERE uid = ?", (Fuid,))
            message = "Thesis approved successfully!"
        elif action == "reject":
            cur.execute("UPDATE grad_student SET thesis_submitted = 0, thesis_approved = 0 WHERE uid = ?", (Fuid,))
            cur.execute("DELETE FROM thesis WHERE student_uid = ?", (Fuid,))
            message = "Thesis rejected."
        else:
            message = "No action taken."
            connection.commit()
            connection.close()
            return render_template("viewThesis.html", success=message, user=user, student=student, thesis=thesis)
        
        cur.execute("SELECT g.*, u.first_name AS fname, u.last_name AS lname FROM grad_student g JOIN users u ON u.uid = g.uid WHERE g.uid = ? AND g.advisor_uid = ?", (Fuid, loggedin))
        student = cur.fetchone()
        
        connection.commit()
        connection.close()
        return render_template("viewThesis.html", success=message, user=user, student=student, thesis=thesis)
    else:
        connection.close()
        return render_template("viewThesis.html", user=user, student=student, thesis=thesis)


@app.route('/processGraduation/<int:uid>', methods=['POST'])
def processGraduation(uid):
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    cur.execute("SELECT * FROM grad_student WHERE uid = ?", (uid,))
    student = cur.fetchone()

    if not student:
        connection.close()
        return render_template("gsHome.html", error="Student not found.")

    if student['form1_submitted'] == 0:
        connection.close()
        return render_template("gsHome.html", error="Student has NOT submitted a Form.")
    
    if not student['graduation_requested']:
        connection.close()
        return render_template("gsHome.html", error="Student has NOT requested graduation.")
    
    cur.execute("""SELECT C.crn AS course_number, C.course_title AS course_name FROM form_courses FC 
                JOIN courses C ON FC.crn = C.crn
                LEFT JOIN transcript T  ON FC.student_uid = T.student_uid AND FC.crn = T.crn
                WHERE FC.student_uid = ? AND T.crn IS NULL""", (uid,))
    missedClasses = cur.fetchall()

    if missedClasses:
        cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
        connection.commit()
        connection.close()
        return render_template("gsHome.html", error="Student has not completed all the courses required in the Form.")

    gpa = student['gpa']
    program = student['program']
    if program == "MS in Computer Science" and gpa < 3.0:
        cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
        connection.commit()
        connection.close()
        return render_template("gsHome.html", error="Student does not meet the 3.0 GPA requirement for MS.")
    elif program == "PhD in Computer Science":
        if gpa < 3.5:
            cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
            connection.commit()
            connection.close()
            return render_template("gsHome.html", error="Student does not meet the 3.4 GPA requirement for PhD.")
        if student['thesis_submitted'] == 0:
            cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
            connection.commit()
            connection.close()
            return render_template("gsHome.html", error="PhD student has not submitted the thesis.")
        if student['thesis_approved'] == 0:
            cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
            connection.commit()
            connection.close()
            return render_template("gsHome.html", error="PhD student thesis has not been approved by the advisor.")
    elif program not in ["MS in Computer Science", "PhD in Computer Science"]:
        cur.execute("UPDATE grad_student SET graduation_requested = 0 WHERE uid = ?", (uid,))
        connection.commit()
        connection.close()
        return render_template("gsHome.html", error="Unknown program.")

    semYear = "Spring 2025"
    degree = program
    cur.execute("INSERT INTO alumni (uid, graduation_semester, Degree) VALUES (?, ?, ?)", (uid, semYear, degree))
    cur.execute("UPDATE users SET user_type = 6 WHERE uid = ?", (uid,))
    cur.execute("DELETE FROM grad_student WHERE uid = ?", (uid,))
    connection.commit()
    connection.close()

    return render_template("gsHome.html", success=f"Student (uid={uid}) has graduated successfully.")

@app.route('/resetdb', methods=['POST'])
def resetdb():

    connection = sqlite3.connect("phase-2.db")
    cur = connection.cursor()
    try:
        with open ('phase-2.sql', 'r') as f:
            sql_script = f.read()
            cur.executescript(sql_script)
        connection.commit()
    except Exception as e:
        return render_template("login.html", error="idk something went wrong")
    finally:
        connection.close()
    
    return render_template("login.html", success="Database Reset!")

#courses 
@app.route('/coursesnpreqs', methods=['GET'])
def coursesnpreqs():
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()

    cur.execute("SELECT c.crn AS course_id, c.course_title AS course_name, d.d_name AS dept, c.crn AS course_number, c.credits FROM courses c JOIN department d ON c.d_num = d.d_num ORDER BY course_id")
    all = cur.fetchall()
    courses = []
    for course in all:
        cur.execute("SELECT c.course_title AS course_name FROM prerequisite p JOIN courses c ON p.prereq_id = c.crn WHERE p.course_id = ?", (course["course_id"],))
        prereqs = cur.fetchall()
        if prereqs:
            names  = []
            for row in prereqs:
                names.append(row["course_name"])
        else:
            names = ["nah you dont need any prereqs"]

        courses.append({
                "course_id": course["course_id"],
                "course_name": course["course_name"],
                "dept": course["dept"],
                "course_number": course["course_number"],
                "credits": course["credits"],
                "prerequisites": names})

    connection.close()
    return render_template("coursesnpreqs.html", courses=courses)


# START REGS

def get_faculty_uid(uid):
    conn = get_db_connection()
    row  = conn.execute(
        "SELECT u.uid FROM users u JOIN faculty f ON u.uid = f.uid WHERE u.uid = ?",
        (uid,)
    ).fetchone()
    conn.close()
    return row['uid'] if row else None


@app.route('/alumni/home')
def alumni_home():
    # only alumni (user_type = 5) may see this
    if 'username' not in session or session.get('user_type') != 6:
        flash('Please log in as alumni.', 'error')
        return redirect(url_for('login', next=request.url))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT first_name, last_name FROM users WHERE username = ?",
        (session['username'],)
    ).fetchone()
    conn.close()

    return render_template(
        'REGS-alumni.html',
        first_name=user['first_name'],
        last_name=user['last_name']
    )
#REGISTER COURSE TO DROP COURSE

@app.route('/register_course', methods=['POST'])
def register_course():
    if 'uid' not in session:
        return redirect(url_for('login'))

    crn = request.form.get('course_id')
    semester = request.form.get('semester', 'Spring 25')
    if semester not in ['Spring 25', 'Fall 25']:
        semester = 'Spring 25'  # Default to Spring if invalid

    conn = get_db_connection()
    cursor = conn.cursor()
    error = None
    success = None

    cursor.execute("""
        SELECT u.uid, g.has_advising_hold
        FROM users u
        JOIN grad_student g ON u.uid = g.uid
        WHERE u.uid = ?
    """, (session['uid'],))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return render_register_page_for(semester, error="Student not found.")
    
    if student['has_advising_hold']:
        conn.close()
        return render_register_page_for(semester, error="Advising Hold - Submit Form 1 first!")

    sid = student['uid']

    cursor.execute("""
        SELECT SUM(c.credits) as current_credits
        FROM transcript t
        JOIN courses c ON t.crn = c.crn
        WHERE t.student_uid = ? AND t.semester = ? AND t.grade = 'IP'
    """, (sid, semester))
    current_credits = cursor.fetchone()['current_credits'] or 0


    cursor.execute("SELECT credits FROM courses WHERE crn = ?", (crn,))
    course_data = cursor.fetchone()
    if not course_data:
        conn.close()
        return render_register_page_for(semester, error="Course not found!")
    
    new_credits = course_data['credits']
    total_credits = current_credits + new_credits

    # BLOCK REGISTRATION IF OVER 18 CREDITS
    if total_credits > 18:
        conn.close()
        return render_register_page_for(
            semester,
            error=f"Cannot register - would exceed 18 credits (Current: {current_credits}, New: {new_credits})"
        )
    
    cursor.execute("""
        SELECT 1 FROM transcript
        WHERE student_uid = ? AND crn = ?
    """, (sid, crn))
    if cursor.fetchone():
        conn.close()
        return render_register_page_for(semester, error=f"You have already taken this course (CRN: {crn})")

    # Check prerequisites
    cursor.execute("""
        SELECT p.prereq_id, c.course_title
        FROM prerequisite p
        JOIN courses c ON p.prereq_id = c.crn
        WHERE p.course_id = ?
    """, (crn,))
    prereqs = cursor.fetchall()

    missing_prereqs = []
    for prereq in prereqs:
        cursor.execute("""
            SELECT 1 FROM transcript
            WHERE student_uid = ? AND crn = ? AND grade != 'F'
        """, (sid, prereq['prereq_id']))
        if not cursor.fetchone():
            missing_prereqs.append(prereq['course_title'])

    if missing_prereqs:
        conn.close()
        return render_register_page_for(semester, error=f"Cannot register - missing prerequisites: {', '.join(missing_prereqs)}")

    # Check if course is offered in the selected semester
    cursor.execute("""
        SELECT current_enrollment, max_enrollment
        FROM schedule
        WHERE crn = ? AND semester = ?
    """, (crn, semester))
    enrollment = cursor.fetchone()
    
    if not enrollment:
        conn.close()
        return render_register_page_for(semester, error=f"Course not offered in {semester}")
    elif enrollment['current_enrollment'] >= enrollment['max_enrollment']:
        conn.close()
        return render_register_page_for(semester, error="Course is already full")

    # If we get here, all checks passed - proceed with registration
    try:
        cursor.execute("""
            INSERT INTO transcript (student_uid, crn, semester, grade)
            VALUES (?, ?, ?, 'IP')
        """, (sid, crn, semester))

        cursor.execute("""
            UPDATE schedule
            SET current_enrollment = current_enrollment + 1
            WHERE crn = ? AND semester = ?
        """, (crn, semester))

        conn.commit()
        success = f"Registered successfully! Total credits: {total_credits}/18"

    except sqlite3.IntegrityError:
        error = "Already registered for this course!"
    except Exception as e:
        error = f"Error: {str(e)}"
    finally:
        conn.close()

    return render_register_page_for(
        semester,
        search_term=None,
        error=error,
        success=success
    )


def render_register_page_for(semester, search_term='', error=None, success=None):
    """Fetches courses + IP regs for exactly one semester, then renders."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # (1) verify grad student
    cursor.execute("""
        SELECT u.uid
          FROM users u
          JOIN grad_student g ON u.uid = g.uid
         WHERE u.uid = ?
    """, (session.get('uid'),))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return render_template('REGS-register.html',
                             courses=[],
                             registered_courses=[],
                             semester=semester,
                             search_term=search_term,
                             total_credits=0,
                             error="Student not found",
                             success=None)

    sid = student['uid']

    # Get all CRNs the student has ever taken (for disabling buttons)
    cursor.execute("""
        SELECT crn FROM transcript WHERE student_uid = ?
    """, (sid,))
    registered_crns = {row['crn'] for row in cursor.fetchall()}

    # (2) available courses in that semester (with optional search)
    sql = """
        SELECT
            c.crn,
            c.course_title,
            c.credits,
            s.day,
            s.time,
            s.semester,
            u.first_name || ' ' || u.last_name AS instructor,
            s.current_enrollment,
            s.max_enrollment
          FROM courses c
          JOIN schedule s     ON c.crn = s.crn
          JOIN faculty f      ON s.instructor_uid = f.uid
          JOIN users u        ON f.uid = u.uid
         WHERE s.semester = ?
    """
    params = [semester]
    if search_term:
        sql += " AND (CAST(c.crn AS TEXT) LIKE ? OR c.course_title LIKE ?)"
        params += [f"%{search_term}%", f"%{search_term}%"]
    sql += " ORDER BY c.crn"
    cursor.execute(sql, params)

    courses = []
    for r in cursor.fetchall():
        cursor.execute("""
            SELECT c.course_title
              FROM prerequisite p
              JOIN courses c ON p.prereq_id = c.crn
             WHERE p.course_id = ?
        """, (r['crn'],))
        prereqs = [p['course_title'] for p in cursor.fetchall()] or ['None']

        courses.append({**r, 'prereqs': prereqs})

    # (3) only IP regs **for that same semester**
    cursor.execute("""
        SELECT
            t.crn,
            c.course_title,
            c.credits,
            t.semester,
            s.day,
            s.time
          FROM transcript t
          JOIN courses  c ON t.crn = c.crn
          JOIN schedule s ON t.crn = s.crn
                         AND t.semester = s.semester
         WHERE t.student_uid = ? 
           AND t.grade = 'IP'
           AND t.semester = ?
         ORDER BY t.crn
    """, (sid, semester))
    registered = cursor.fetchall()

    conn.close()
    total_credits = sum(r['credits'] for r in registered)

    return render_template('REGS-register.html',
                         courses=courses,
                         registered_courses=registered,
                         semester=semester,
                         search_term=search_term,
                         total_credits=total_credits,
                         registered_crns=registered_crns,
                         error=error,
                         success=success)

@app.route('/register/spring', methods=['GET'])
def register_spring():
    # GET /register/spring?search=CSCI
    term = request.args.get('search', '').strip()
    return render_register_page_for('Spring 25', search_term=term)

@app.route('/register/fall', methods=['GET'])
def register_fall():
    term = request.args.get('search', '').strip()
    return render_register_page_for('Fall 25', search_term=term)
# Helper functions updated for new schema:

def times_overlap(time1, time2):
    time1_parts = time1.split('—')
    time2_parts = time2.split('—')
    time1_start = int(time1_parts[0])
    time1_end = int(time1_parts[1])
    time2_start = int(time2_parts[0])
    time2_end = int(time2_parts[1])
    
    return ((time1_start >= time2_start and time1_start < time2_end) or
            (time2_start >= time1_start and time2_start < time1_end) or
            (time1_start <= time2_start and time1_end >= time2_end) or
            (time2_start <= time1_start and time2_end >= time1_end))

def has_taken_course(student_id, crn):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM transcript
        WHERE student_uid = ? AND crn = ? AND grade NOT IN ('F', 'IP')
    """, (student_id, crn))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def check_prerequisites(student_id, crn):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT prereq_id
        FROM prerequisite
        WHERE course_id = ?
    """, (crn,))
    prereqs = cursor.fetchall()
    
    missing = []
    for prereq in prereqs:
        prereq_id = prereq[0]
        cursor.execute("""
            SELECT grade
            FROM transcript
            WHERE student_uid = ? AND crn = ? AND grade NOT IN ('F', 'IP', '')
        """, (student_id, prereq_id))
        if not cursor.fetchone():
            cursor.execute("SELECT course_title FROM courses WHERE crn = ?", (prereq_id,))
            title = cursor.fetchone()
            missing.append(title[0] if title else prereq_id)
    
    conn.close()
    return missing


@app.route('/register_page', methods=['GET'])
def show_register_page():
    if 'uid' not in session:
        return redirect(url_for('login'))

    # pick up semester from query (default to Spring 25)
    semester = request.args.get('semester', 'Spring 25')
    search_term = request.args.get('search', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # verify grad student
    cursor.execute("""
        SELECT u.uid
          FROM users u
          JOIN grad_student g ON u.uid = g.uid
         WHERE u.uid = ?
    """, (session['uid'],))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return render_template("REGS-register.html",
                               courses=[],
                               registered_courses=[],
                               error="Student not found",
                               semester=semester,
                               search_term=search_term,
                               total_credits=0)

    student_id = student['uid']

    # fetch available courses filtered by semester
    sql = """
        SELECT
            c.crn,
            c.course_title,
            c.credits,
            s.day,
            s.time,
            s.semester,
            u.first_name || ' ' || u.last_name AS instructor,
            s.current_enrollment,
            s.max_enrollment
          FROM courses c
          JOIN schedule s     ON c.crn = s.crn
          JOIN faculty f      ON s.instructor_uid = f.uid
          JOIN users u        ON f.uid = u.uid
         WHERE s.semester = ?
    """
    params = [semester]
    if search_term:
        sql += "  AND (CAST(c.crn AS TEXT) LIKE ? OR c.course_title LIKE ?)"
        like = f"%{search_term}%"
        params += [like, like]
    sql += " ORDER BY c.crn"
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    courses = []
    for r in rows:
        # fetch prereqs
        cursor.execute("""
            SELECT c.course_title
              FROM prerequisite p
              JOIN courses c ON p.prereq_id = c.crn
             WHERE p.course_id = ?
        """, (r['crn'],))
        prereqs = [p['course_title'] for p in cursor.fetchall()] or ['None']

        courses.append({
            **r,
            'prereqs': prereqs
        })

    # fetch in-progress registrations (IP) for this student
    cursor.execute("""
        SELECT
            t.crn,
            c.course_title,
            c.credits,
            t.semester,
            s.day,
            s.time
          FROM transcript t
          JOIN courses c  ON t.crn = c.crn
          JOIN schedule s ON t.crn = s.crn
                         AND t.semester = s.semester
         WHERE t.student_uid = ? AND t.grade = 'IP'
         ORDER BY t.semester, t.crn
    """, (student_id,))
    registered = cursor.fetchall()
    conn.close()

    total_credits = sum(c['credits'] for c in registered)

    if semester == 'Spring 25':
        return render_register_page_for('Spring 25', search_term=None)
    else:
        return render_register_page_for('Fall 25', search_term=None)

@app.route('/drop_course', methods=['POST'])
def drop_course():
    if 'uid' not in session:
        return redirect(url_for('login'))

    crn      = request.form.get('course_id')
    semester = request.form.get('semester', 'Spring 25')
    conn = get_db_connection()
    cursor = conn.cursor()

    # verify student
    cursor.execute("""
        SELECT u.uid
          FROM users u
          JOIN grad_student g ON u.uid = g.uid
         WHERE u.uid = ?
    """, (session['uid'],))
    student = cursor.fetchone()

    error = None
    success = None
    if not student:
        error = "Student not found."
    else:
        sid = student['uid']
        # delete enrollment
        cursor.execute("""
            DELETE FROM transcript
             WHERE student_uid = ? AND crn = ? AND semester = ?
        """, (sid, crn, semester))
        # decrement enrollment
        cursor.execute("""
            UPDATE schedule
               SET current_enrollment = current_enrollment - 1
             WHERE crn = ? AND semester = ?
        """, (crn, semester))
        conn.commit()
        success = "Course successfully dropped!"

        # warn if below min credits
        cursor.execute("""
            SELECT SUM(c.credits)
              FROM transcript t
              JOIN courses c ON t.crn = c.crn
             WHERE t.student_uid = ? AND t.grade = 'IP'
        """, (sid,))
        curr = cursor.fetchone()[0] or 0
        if curr < 12:
            success += f" Note: you currently have {curr} credits; minimum is 12."

    # re-query available courses for the same semester
    cursor.execute("""
        SELECT
            c.crn,
            c.course_title,
            c.credits,
            s.day,
            s.time,
            s.semester,
            u.first_name || ' ' || u.last_name AS instructor,
            s.current_enrollment,
            s.max_enrollment
          FROM courses c
          JOIN schedule s     ON c.crn = s.crn
          JOIN faculty f      ON s.instructor_uid = f.uid
          JOIN users u        ON f.uid = u.uid
         WHERE s.semester = ?
         ORDER BY c.crn
    """, (semester,))
    rows = cursor.fetchall()

    courses = []
    for r in rows:
        cursor.execute("""
            SELECT c.course_title
              FROM prerequisite p
              JOIN courses c ON p.prereq_id = c.crn
             WHERE p.course_id = ?
        """, (r['crn'],))
        prereqs = [p['course_title'] for p in cursor.fetchall()] or ['None']
        courses.append({**r, 'prereqs': prereqs})

    # re-query registered courses
    registered = []
    if student:
        sid = student['uid']
        cursor.execute("""
            SELECT
                t.crn,
                c.course_title,
                c.credits,
                t.semester,
                s.day,
                s.time
              FROM transcript t
              JOIN courses c  ON t.crn = c.crn
              JOIN schedule s ON t.crn = s.crn
                             AND t.semester = s.semester
             WHERE t.student_uid = ? AND t.grade = 'IP'
             ORDER BY t.semester, t.crn
        """, (sid,))
        registered = cursor.fetchall()
    conn.close()

    total_credits = sum(c['credits'] for c in registered)

    if semester == 'Spring 25':
        return render_register_page_for('Spring 25', search_term=None, error=error, success=success)
    else:
        return render_register_page_for('Fall 25',   search_term=None, error=error, success=success)


@app.route('/course_schedule')
def course_schedule():
    search_term      = request.args.get('search', '').strip()
    selected_semester = request.args.get('semester', 'Spring 25')
    if selected_semester not in ['Spring 25','Fall 25']:
        selected_semester = 'Spring 25'

    params = [selected_semester]
    query = """
    SELECT
      c.crn,
      c.course_title   AS title,
      d.d_name         AS department,
      c.credits,
      s.day,
      s.time,
      s.room_num,
      u.first_name || ' ' || u.last_name AS instructor,
      COALESCE(
        GROUP_CONCAT(pr.course_title, ', '),
        'None'
      ) AS prerequisites
    FROM courses c
    JOIN department d  ON c.d_num       = d.d_num
    JOIN schedule s    ON c.crn         = s.crn
    JOIN users u       ON s.instructor_uid = u.uid
    -- bring in zero or more prereqs via your existing table
    LEFT JOIN prerequisite p ON c.crn      = p.course_id
    LEFT JOIN courses pr       ON p.prereq_id = pr.crn
    WHERE s.semester = ?
    """

    if search_term:
        query += """
        AND (
          CAST(c.crn AS TEXT) LIKE ? OR
          c.course_title LIKE ? OR
          d.d_name       LIKE ? OR
          u.first_name   LIKE ? OR
          u.last_name    LIKE ?
        )
        """
        pattern = f"%{search_term}%"
        params.extend([pattern]*5)

    query += """
    GROUP BY c.crn
    ORDER BY c.crn
    """

    conn    = get_db_connection()
    courses = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
      'REGS-course_schedule.html',
      courses=courses,
      search_term=search_term,
      selected_semester=selected_semester
    )

@app.route('/classes_taught')
def classes_taught():
    # only faculty may access
    if 'uid' not in session:
        return redirect(url_for('login'))

    # determine which semester to show
    selected_semester = request.args.get('semester', 'Spring 25')
    valid_terms = ['Spring 25', 'Fall 25']
    if selected_semester not in valid_terms:
        selected_semester = 'Spring 25'

    conn = get_db_connection()
    # map user -> faculty
    faculty_row = conn.execute(
        """
        SELECT u.uid
        FROM users u
        JOIN faculty f ON u.uid = f.uid
        WHERE u.uid = ?
        """,
        (session['uid'],)
    ).fetchone()
    if not faculty_row:
        conn.close()
        return redirect(url_for('home', error="Faculty not found"))
    faculty_uid = faculty_row['uid']

    # fetch courses for that faculty & semester
    courses = conn.execute(
        """
        SELECT
            s.crn,
            c.course_title,
            s.semester,
            s.day,
            s.time,
            s.section_num
        FROM schedule s
        JOIN courses c ON s.crn = c.crn
        WHERE s.instructor_uid = ? AND s.semester = ?
        ORDER BY s.semester, s.crn
        """,
        (faculty_uid, selected_semester)
    ).fetchall()

    # build rosters
    course_rosters = []
    for course in courses:
        roster = conn.execute(
            """
            SELECT
                u.uid,
                u.first_name,
                u.last_name,
                g.program,
                t.grade
            FROM transcript t
            JOIN users u ON t.student_uid = u.uid
            JOIN grad_student g ON u.uid = g.uid
            WHERE t.crn = ? AND t.semester = ?
            ORDER BY u.last_name, u.first_name
            """,
            (course['crn'], course['semester'])
        ).fetchall()
        course_rosters.append({
            'course': course,
            'students': roster
        })

    conn.close()
    return render_template(
        'REGS-classes_taught.html',
        course_rosters=course_rosters,
        selected_semester=selected_semester
    )


# drop down to enter grade 
#submit grades button
#directly change the grade student has in transcipt for their class
#error if they try to grade again

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    # only faculty (3) or admin (4) may submit grades
    if 'uid' not in session:
        return redirect(url_for('login'))

    course_id = request.form.get('course_id')
    semester = request.form.get('semester')
    conn = get_db_connection()

    # if faculty, verify they teach this course
    if session['user_type'] == 3:
        s_row = conn.execute(
            "SELECT instructor_uid FROM schedule WHERE crn = ? AND semester = ?",
            (course_id, semester)
        ).fetchone()
        if not s_row or s_row['instructor_uid'] != get_faculty_uid(session['uid']): ###??????????????????????????????????????
            flash('Not authorized to grade this course.', 'error')
            conn.close()
            return redirect(url_for('classes_taught'))

    # update each posted grade
    for key, value in request.form.items():
        if not key.startswith('grade_') or not value:
            continue
        student_uid = key.split('_', 1)[1]
        # only update if still 'IP' (in progress)
        current = conn.execute(
            "SELECT grade FROM transcript WHERE student_uid = ? AND crn = ? AND semester = ?",
            (student_uid, course_id, semester)
        ).fetchone()
        if not current or current['grade'] != 'IP':
            continue
        conn.execute(
            "UPDATE transcript SET grade = ?, grade_edited = 1 WHERE student_uid = ? AND crn = ? AND semester = ?",
            (value, student_uid, course_id, semester)
        )

    conn.commit()
    conn.close()
    flash('Grades submitted successfully.', 'success')
    return redirect(url_for('classes_taught'))

@app.route('/view_student_transcript/<int:student_id>')
def view_student_transcript(student_id):
    # only faculty (user_type = 3) may access
    if 'uid' not in session:
        return redirect(url_for('login'))

    course_id = request.args.get('course_id')
    semester = request.args.get('semester')
    if not course_id or not semester:
        return redirect(url_for('classes_taught', error = "Course ID and Semester Are Required"))

    conn = get_db_connection()

    # verify faculty identity
    fac = conn.execute(
        "SELECT u.uid FROM users u JOIN faculty f ON u.uid = f.uid WHERE u.uid = ?",
        (session['uid'],)
    ).fetchone()
    if not fac:
        flash('Faculty record not found.', 'error')
        conn.close()
        return redirect(url_for('classes_taught'))
    faculty_uid = fac['uid']

    # verify this faculty teaches the course in that semester
    teach = conn.execute(
        "SELECT 1 FROM schedule WHERE crn = ? AND semester = ? AND instructor_uid = ?",
        (course_id, semester, faculty_uid)
    ).fetchone()
    if not teach:
        flash("You don't teach this course.", 'error')
        conn.close()
        return redirect(url_for('classes_taught'))

    # verify student is enrolled
    enrolled = conn.execute(
        "SELECT 1 FROM transcript WHERE student_uid = ? AND crn = ? AND semester = ?",
        (student_id, course_id, semester)
    ).fetchone()
    if not enrolled:
        flash('Student is not enrolled in this course.', 'error')
        conn.close()
        return redirect(url_for('classes_taught'))

    # fetch the transcript entry
    transcript = conn.execute(
        """
        SELECT
            c.crn,
            c.course_title,
            c.credits,
            t.semester,
            t.grade,
            u.first_name || ' ' || u.last_name AS instructor
        FROM transcript t
        JOIN courses c ON t.crn = c.crn
        JOIN schedule s ON s.crn = t.crn AND s.semester = t.semester
        JOIN users u ON s.instructor_uid = u.uid
        WHERE t.student_uid = ? AND t.crn = ? AND t.semester = ?
        """,
        (student_id, course_id, semester)
    ).fetchall()

    # fetch student info
    student = conn.execute(
        """
        SELECT u.uid, u.first_name, u.last_name, g.program
        FROM users u
        JOIN grad_student g ON u.uid = g.uid
        WHERE u.uid = ?
        """,
        (student_id,)
    ).fetchone()
    conn.close()

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('classes_taught'))

    return render_template('REGS-faculty_transcript_view.html', transcript=transcript, student=student)

@app.route('/all_students')
def all_students():
    # only admin (3) or grad secretary (4) may view all students
    if 'uid' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    students = conn.execute(
        """
        SELECT g.uid,
               u.first_name,
               u.last_name,
               g.program
        FROM grad_student g
        JOIN users u ON g.uid = u.uid
        ORDER BY u.last_name, u.first_name
        """
    ).fetchall()
    conn.close()

    return render_template('REGS-all_students.html', students=students)


@app.route('/admin/all_students')
def admin_all_students():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()

    if search_term:
        like = f'%{search_term}%'
        students = conn.execute(
            """
            SELECT g.uid,
                   u.first_name,
                   u.last_name,
                   g.program
            FROM grad_student g
            JOIN users u ON g.uid = u.uid
            WHERE u.first_name LIKE ?
               OR u.last_name  LIKE ?
               OR g.uid         LIKE ?
            ORDER BY u.last_name, u.first_name
            """,
            (like, like, like)
        ).fetchall()
    else:
        students = conn.execute(
            """
            SELECT g.uid,
                   u.first_name,
                   u.last_name,
                   g.program
            FROM grad_student g
            JOIN users u ON g.uid = u.uid
            ORDER BY u.last_name, u.first_name
            """
        ).fetchall()

    conn.close()
    return render_template(
        'REGS-admin_all_students.html',
        students=students,
        search_term=search_term
    )


'''@app.route('/transcript')
def view_transcript():
    # only grad students (1) or alumni (5) may view their transcript
    if 'username' not in session or session.get('user_type') not in [2, 6]:
        flash('Please log in as a graduate student or alumni.', 'error')
        return redirect(url_for('login', next=request.url))

    conn = get_db_connection()
    if session['user_type'] == 2:
        row = conn.execute(
            "SELECT u.uid FROM users u JOIN grad_student g ON u.uid = g.uid WHERE u.username = ?",
            (session['username'],)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT u.uid FROM users u JOIN alumni a ON u.uid = a.uid WHERE u.username = ?",
            (session['username'],)
        ).fetchone()

    if not row:
        flash('User record not found.', 'error')
        conn.close()
        return redirect(url_for('home'))

    student_uid = row['uid']
    transcript = conn.execute(
        """
        SELECT
            t.crn,
            c.course_title,
            c.credits,
            t.semester,
            t.grade
        FROM transcript t
        JOIN courses c ON t.crn = c.crn
        WHERE t.student_uid = ?
        ORDER BY t.semester, t.crn
        """,
        (student_uid,)
    ).fetchall()
    conn.close()

    gpa = gpa_calculator(transcript)
    return render_template(
        'REGS-transcript.html',
        transcript=transcript,
        gpa=gpa
    )'''

GP = {
    'A': 4.0,
    'A-': 3.7,
    'B+': 3.3,
    'B': 3.0,
    'B-': 2.7,
    'C+': 2.3,
    'C': 2.0,
    'F': 0.0
}

def gpa_calculator(transcript):
    total_points = 0
    total_credits = 0
    for rec in transcript:
        grade = rec['grade']
        credits = rec['credits']
        if grade in GP:
            total_points += GP[grade] * credits
            total_credits += credits
    if total_credits == 0:
        return 0.0
    return round(total_points / total_credits, 2)


'''@app.route('/search_student', methods=['GET', 'POST'])
def search_student():
    if 'username' not in session or session.get('user_type') != 5:
        flash('Please log in as a graduate secretary.', 'error')
        return redirect(url_for('login', next=request.url))

    students = None
    search_term = ''
    if request.method == 'POST':
        search_term = request.form.get('search_term', '').strip()
        like = f"%{search_term}%"
        conn = get_db_connection()
        students = conn.execute(
            """
            SELECT g.uid,
                   u.first_name,
                   u.last_name,
                   g.program
            FROM grad_student g
            JOIN users u ON g.uid = u.uid
            WHERE u.first_name LIKE ?
               OR u.last_name  LIKE ?
               OR g.uid         LIKE ?
            ORDER BY u.last_name, u.first_name
            """,
            (like, like, like)
        ).fetchall()
        conn.close()

    return render_template(
        'REGS-search_student.html',
        students=students,
        search_term=search_term
    )'''

@app.route('/admin/admin_search_student', methods=['GET', 'POST'])
def admin_search_student():
    # only admins (user_type = 3) may search students
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    students = None
    search_term = ''
    if request.method == 'POST':
        search_term = request.form.get('search_term', '').strip()
        like = f"%{search_term}%"
        conn = get_db_connection()
        students = conn.execute(
            """
            SELECT g.uid,
                   u.first_name,
                   u.last_name,
                   g.program
            FROM grad_student g
            JOIN users u ON g.uid = u.uid
            WHERE u.first_name LIKE ?
               OR u.last_name  LIKE ?
               OR g.uid         LIKE ?
            ORDER BY u.last_name, u.first_name
            """,
            (like, like, like)
        ).fetchall()
        conn.close()

    return render_template(
        'REGS-admin_search_student.html',
        students=students,
        search_term=search_term
    )


@app.route('/view_gs_transcript/<student_id>')
def view_gs_transcript(student_id):
    if 'uid' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    transcript = conn.execute("""
        SELECT
            t.crn,
            c.course_title,
            c.credits,
            t.semester,
            t.grade
        FROM transcript t
        JOIN courses c 
          ON t.crn = c.crn
        WHERE t.student_uid = ?
        ORDER BY t.semester, t.crn
    """, (student_id,)).fetchall()

    # fetch student info
    student = conn.execute(
        """
        SELECT u.uid,
               u.first_name,
               u.last_name,
               g.program
        FROM grad_student g
        JOIN users u ON g.uid = u.uid
        WHERE g.uid = ?
        """,
        (student_id,)
    ).fetchone()
    conn.close()

    if not student:
        flash('Student not found.', 'error')
        return render_template('REGS-gs_transcript_view.html', transcript=[], student=None)

    gpa = gpa_calculator(transcript)
    return render_template(
        'REGS-gs_transcript_view.html',
        transcript=transcript,
        student=student,
        gpa=gpa
    )

@app.route('/update_grade', methods=['POST'])
def update_grade():
    # only faculty (2), admin (3) or grad‑secretary (4) may update grades
    if 'uid' not in session:
        return redirect(url_for('login'))

    student_uid = request.form.get('student_id')
    crn         = request.form.get('course_id')
    semester    = request.form.get('semester')
    new_grade   = request.form.get('new_grade')

    if not new_grade:
        flash('Please select a grade before submitting.', 'error')
        if session['user_type'] == 5:
            return redirect(url_for('view_gs_transcript', student_id=student_uid))
        else:
            return redirect(url_for('admin_view_transcript', student_id=student_uid))

    conn = get_db_connection()

    # if faculty, verify they teach this course in that semester
    if session['user_type'] == 3:
        fac = conn.execute(
            "SELECT u.uid FROM users u JOIN faculty f ON u.uid=f.uid WHERE u.uid = ?",
            (session['uid'],)
        ).fetchone()
        if not fac:
            flash('Faculty record not found.', 'error')
            conn.close()
            return redirect(url_for('classes_taught'))

        teaches = conn.execute(
            "SELECT 1 FROM schedule WHERE crn = ? AND semester = ? AND instructor_uid = ?",
            (crn, semester, fac['uid'])
        ).fetchone()
        if not teaches:
            flash('You are not authorized to grade this course.', 'error')
            conn.close()
            return redirect(url_for('classes_taught'))

    # update the grade
    conn.execute(
        """
        UPDATE transcript
           SET grade = ?,
               grade_edited = 1
         WHERE student_uid = ?
           AND crn         = ?
           AND semester    = ?
        """,
        (new_grade, student_uid, crn, semester)
    )
    conn.commit()
    conn.close()

    flash('Grade updated successfully!', 'success')
    if session['user_type'] == 5:
        return redirect(url_for('view_gs_transcript', student_id=student_uid))
    else:
        return redirect(url_for('admin_view_transcript', student_id=student_uid))

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    # only admins (user_type = 3) may register new grad students
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        uid_str      = request.form.get('uid', '').strip()
        email        = request.form.get('email', '').strip()
        username     = request.form.get('username', '').strip()
        first_name   = request.form.get('first_name', '').strip()
        last_name    = request.form.get('last_name', '').strip()
        address      = request.form.get('address', '').strip()
        program      = request.form.get('program', '').strip()
        d_num        = request.form.get('d_num', '').strip()
        advisor_uid  = request.form.get('advisor_uid', '').strip()
        password     = request.form.get('password', '')
        confirm_pass = request.form.get('confirm_password', '')

        # basic validations
        if password != confirm_pass:
            flash('Passwords do not match.', 'error')
            return render_template('REGS-register_student.html'), 400
        if not re.fullmatch(r'\d{8}', uid_str):
            flash('UID must be exactly 8 digits.', 'error')
            return render_template('REGS-register_student.html'), 400

        conn = get_db_connection()
        # uniqueness checks
        if conn.execute("SELECT 1 FROM users WHERE uid = ?", (uid_str,)).fetchone():
            flash('This UID is already taken.', 'error')
            conn.close()
            return render_template('REGS-register_student.html'), 400
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            flash('Username already taken.', 'error')
            conn.close()
            return render_template('REGS-register_student.html'), 400
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            flash('Email already registered.', 'error')
            conn.close()
            return render_template('REGS-register_student.html'), 400

        # insert into users (storing raw password in password_hash column)
        conn.execute(
            """
            INSERT INTO users
              (uid, email, username, password_hash, user_type, first_name, last_name, address)
            VALUES
              (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (uid_str, email, username, password, first_name, last_name, address)
        )
        # insert into grad_student
        conn.execute(
            """
            INSERT INTO grad_student
              (uid, advisor_uid, d_num, program)
            VALUES
              (?, ?, ?, ?)
            """,
            (uid_str, advisor_uid, d_num, program)
        )
        conn.commit()
        conn.close()

        flash('Graduate student registered successfully!', 'success')
        return redirect(url_for('admin_all_students'))

    return render_template('REGS-register_student.html')

@app.route('/admin')
def admin_home():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    return render_template('REGS-admin.html')

@app.route('/admin/manage_courses', methods=['GET', 'POST'])
def admin_manage_courses():
    if 'uid' not in session:
        return redirect(url_for('login'))

    error = None
    success = None
    
    if request.method == 'POST':
        crn = request.form.get('crn')
        course_title = request.form.get('coursetitle')
        d_num = request.form.get('d_num')
        credits = request.form.get('credits')
        description = request.form.get('description', '')
        instructor_uid = request.form.get('instructor_id')
        semester = request.form.get('semester')
        day = request.form.get('day')
        time = request.form.get('time')
        room_num = request.form.get('roomnum') or "TBD"
        max_enrollment = request.form.get('maxenrollment') or 30
        section_num = request.form.get('sectionnum') or 1
        
        conn = get_db_connection()
        
        try:
            conn.execute("""
                INSERT INTO courses (crn, course_title, d_num, credits, description)
                VALUES (?, ?, ?, ?, ?)
            """, (crn, course_title, d_num, credits, description))
            
            conn.execute("""
                INSERT INTO schedule (crn, section_num, semester, time, day, room_num, 
                                    max_enrollment, current_enrollment, instructor_uid)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (crn, section_num, semester, time, day, room_num, 
                 max_enrollment, instructor_uid))
            
            conn.commit()
            success = "Added a new course successfully!"
        except sqlite3.IntegrityError as e:
            error = f"Error adding course: {str(e)}"
        finally:
            conn.close()
    
    conn = get_db_connection()
    courses = conn.execute("""
        SELECT c.crn, c.course_title, d.d_name, c.credits, s.day, s.time, 
               s.room_num, u.first_name, u.last_name, s.semester 
        FROM courses c 
        JOIN department d ON c.d_num = d.d_num 
        JOIN schedule s ON c.crn = s.crn 
        JOIN users u ON s.instructor_uid = u.uid 
        ORDER BY s.semester, c.crn 
    """).fetchall()
    
    faculty_list = conn.execute("""
        SELECT f.uid, u.first_name, u.last_name 
        FROM faculty f
        JOIN users u ON f.uid = u.uid
        WHERE f.is_instructor = 1
    """).fetchall()
    
    conn.close()
    
    return render_template('REGS-admin_manage_courses.html', 
                         courses=courses, 
                         faculty_list=faculty_list, 
                         error=error, 
                         success=success)

@app.route('/admin/view_gs')
def admin_view_gs():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    if search_term:
        grad_secretaries = conn.execute("""
            SELECT gs.uid, u.first_name, u.last_name, u.email 
            FROM grad_secretary gs
            JOIN users u ON gs.uid = u.uid
            WHERE u.first_name LIKE ? OR u.last_name LIKE ? OR gs.uid LIKE ?
            ORDER BY u.last_name, u.first_name
        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
    else:
        grad_secretaries = conn.execute("""
            SELECT gs.uid, u.first_name, u.last_name, u.email 
            FROM grad_secretary gs
            JOIN users u ON gs.uid = u.uid
            ORDER BY u.last_name, u.first_name
        """).fetchall()
    
    conn.close()
    return render_template('REGS-admin_view_gs.html', grad_secretaries=grad_secretaries, search_term=search_term)

@app.route('/admin/view_faculty')
def admin_view_faculty():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    if search_term:
        faculty = conn.execute("""
            SELECT
                f.uid,
                u.first_name,
                u.last_name,
                u.email,
                d.d_name AS department
            FROM faculty f
            JOIN users u   ON f.uid = u.uid
            JOIN department d ON f.d_num = d.d_num
            WHERE
                u.first_name LIKE ?
                OR u.last_name  LIKE ?
                OR f.uid        LIKE ?
            ORDER BY u.last_name, u.first_name
        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
    else:
        faculty = conn.execute("""
            SELECT
                f.uid,
                u.first_name,
                u.last_name,
                u.email,
                d.d_name AS department
            FROM faculty f
            JOIN users u   ON f.uid = u.uid
            JOIN department d ON f.d_num = d.d_num
            ORDER BY u.last_name, u.first_name
        """).fetchall()
    
    conn.close()
    return render_template(
        'REGS-admin_view_faculty.html',
        faculty=faculty,
        search_term=search_term
    )

@app.route('/admin_view_transcript/<student_id>')
def admin_view_transcript(student_id):
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    error = request.args.get('error')
    success = request.args.get('success')
    conn = get_db_connection()

    # grab the student’s basic info from grad_student + users
    student = conn.execute("""
        SELECT
            gs.uid,
            u.first_name,
            u.last_name,
            gs.program
        FROM grad_student gs
        JOIN users u
          ON gs.uid = u.uid
        WHERE gs.uid = ?
    """, (student_id,)).fetchone()

    # grab their transcript entries
    transcript = conn.execute("""
        SELECT
            t.crn,
            c.course_title   AS coursetitle,
            c.credits,
            t.semester,
            t.grade
        FROM transcript t
        JOIN courses c
          ON t.crn = c.crn
        WHERE t.student_uid = ?
        ORDER BY t.semester
    """, (student_id,)).fetchall()

    conn.close()

    if not student:
        return render_template('REGS-admin_view_transcript.html',error="Student not found.")

    return render_template(
        'REGS-admin_view_transcript.html',
        student=student,
        transcript=transcript,
        error=error,
        success=success
    )

@app.route('/admin/view_classes')
def admin_view_classes():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    # build the base SELECT for courses + instructor
    course_sql = """
        SELECT
            c.crn,
            c.course_title   AS coursetitle,
            s.semester,
            s.day,
            s.time,
            ui.first_name || ' ' || ui.last_name AS instructor_name
        FROM courses c
        JOIN schedule s
          ON c.crn = s.crn
        JOIN faculty f
          ON s.instructor_uid = f.uid
        JOIN users ui
          ON f.uid = ui.uid
    """
    params = []
    if search_term:
        course_sql += """
          WHERE
            c.course_title LIKE ?
            OR ui.first_name   LIKE ?
            OR ui.last_name    LIKE ?
        """
        like = f'%{search_term}%'
        params = [like, like, like]
    course_sql += " ORDER BY s.semester DESC, c.crn"

    courses = conn.execute(course_sql, params).fetchall()
    
    # now for each course, pull its enrolled grad students
    course_rosters = []
    for course in courses:
        students = conn.execute("""
            SELECT
                g.uid,
                us.first_name,
                us.last_name,
                g.program,
                t.grade
            FROM transcript t
            JOIN grad_student g
              ON t.student_uid = g.uid
            JOIN users us
              ON g.uid = us.uid
            WHERE
                t.crn      = ?
              AND t.semester = ?
            ORDER BY us.last_name
        """, (course['crn'], course['semester'])).fetchall()
        
        course_rosters.append({
            'course': course,
            'students': students
        })

    conn.close()
    return render_template(
        'REGS-admin_view_classes.html',
        course_rosters=course_rosters,
        search_term=search_term
    )


@app.route('/admin/view_alumni')
def admin_view_alumni():
    if 'uid' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    if search_term:
        alumni = conn.execute("""
            SELECT
                a.uid,
                u.first_name,
                u.last_name,
                u.email,
                u.username,
                gs.program
            FROM alumni a
            JOIN users u
              ON a.uid = u.uid
            LEFT JOIN grad_student gs
              ON a.uid = gs.uid
            WHERE
                u.first_name LIKE ?
                OR u.last_name  LIKE ?
                OR a.uid        LIKE ?
            ORDER BY u.last_name, u.first_name
        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
    else:
        alumni = conn.execute("""
            SELECT
                a.uid,
                u.first_name,
                u.last_name,
                u.email,
                u.username,
                gs.program
            FROM alumni a
            JOIN users u
              ON a.uid = u.uid
            LEFT JOIN grad_student gs
              ON a.uid = gs.uid
            ORDER BY u.last_name, u.first_name
        """).fetchall()
    
    conn.close()
    return render_template(
        'REGS-admin_view_alumni.html',
        alumni=alumni,
        search_term=search_term
    )

#COULD BE WRONG - TOOK GS AS STUDENT AND NOT grad secretary 
'''@app.route('/gs_course_schedule')
def gs_course_schedule():
    # only grad‑secretaries (gs = 5) can see this
    if 'uid' not in session:
        return redirect(url_for('login'))
    
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    # Base query: course info + dept + schedule + instructor name
    base_sql = """
        SELECT
            c.crn,
            c.course_title   AS coursetitle,
            d.d_name         AS department,
            c.credits,
            s.day,
            s.time,
            ui.first_name    AS instructor_first,
            ui.last_name     AS instructor_last
        FROM courses c
        JOIN department d
          ON c.d_num = d.d_num
        JOIN schedule s
          ON c.crn = s.crn
        LEFT JOIN faculty f
          ON s.instructor_uid = f.uid
        LEFT JOIN users ui
          ON f.uid = ui.uid
        WHERE s.semester = 'Spring 25'
    """
    params = []
    if search_term:
        base_sql += """
          AND (
              CAST(c.crn AS TEXT) LIKE ? OR
              c.course_title     LIKE ? OR
              ui.first_name      LIKE ? OR
              ui.last_name       LIKE ?
          )
        """
        like = f'%{search_term}%'
        params = [like, like, like, like]
    
    base_sql += " ORDER BY c.crn"
    courses = conn.execute(base_sql, params).fetchall()
    
    # For each course, pull its enrolled students
    course_list = []
    total_students = 0
    for course in courses:
        roster = conn.execute("""
            SELECT
                g.uid,
                us.first_name,
                us.last_name,
                t.grade
            FROM transcript t
            JOIN grad_student g
              ON t.student_uid = g.uid
            JOIN users us
              ON g.uid = us.uid
            WHERE t.crn      = ?
              AND t.semester = 'Spring 25'
            ORDER BY us.last_name, us.first_name
        """, (course['crn'],)).fetchall()
        
        cd = dict(course)
        cd['students'] = roster
        course_list.append(cd)
        total_students += len(roster)
    
    conn.close()
    return render_template(
        'REGS-gs_course_schedule.html',
        courses=course_list,
        search_term=search_term,
        total_students=total_students
    )'''
@app.route('/gs_course_schedule')
def gs_course_schedule():
    # only grad-secretaries (gs = 5) can see this
    if 'uid' not in session:
        return redirect(url_for('login'))
    
    search_term = request.args.get('search', '').strip()
    selected_semester = request.args.get('semester', 'Spring 25')
    if selected_semester not in ['Spring 25', 'Fall 25']:
        selected_semester = 'Spring 25'

    conn = get_db_connection()
    
    # Base query: course info + dept + schedule + instructor name
    base_sql = """
        SELECT
            c.crn,
            c.course_title   AS coursetitle,
            d.d_name         AS department,
            c.credits,
            s.day,
            s.time,
            ui.first_name    AS instructor_first,
            ui.last_name     AS instructor_last
        FROM courses c
        JOIN department d
          ON c.d_num = d.d_num
        JOIN schedule s
          ON c.crn = s.crn
        LEFT JOIN faculty f
          ON s.instructor_uid = f.uid
        LEFT JOIN users ui
          ON f.uid = ui.uid
        WHERE s.semester = ?
    """
    params = [selected_semester]
    
    if search_term:
        base_sql += """
          AND (
              CAST(c.crn AS TEXT) LIKE ? OR
              c.course_title     LIKE ? OR
              ui.first_name      LIKE ? OR
              ui.last_name       LIKE ?
          )
        """
        like = f'%{search_term}%'
        params.extend([like, like, like, like])
    
    base_sql += " ORDER BY c.crn"
    courses = conn.execute(base_sql, params).fetchall()
    
    # For each course, pull its enrolled students
    course_list = []
    total_students = 0
    for course in courses:
        roster = conn.execute("""
            SELECT
                g.uid,
                us.first_name,
                us.last_name,
                t.grade
            FROM transcript t
            JOIN grad_student g
              ON t.student_uid = g.uid
            JOIN users us
              ON g.uid = us.uid
            WHERE t.crn      = ?
              AND t.semester = ?
            ORDER BY us.last_name, us.first_name
        """, (course['crn'], selected_semester)).fetchall()
        
        cd = dict(course)
        cd['students'] = roster
        course_list.append(cd)
        total_students += len(roster)
    
    conn.close()
    return render_template(
        'REGS-gs_course_schedule.html',
        courses=course_list,
        search_term=search_term,
        total_students=total_students,
        selected_semester=selected_semester
    )

@app.route('/addfaculty', methods=['GET','POST'])
def addfaculty():
    if request.method == 'POST':
        uid        = request.form['uid'].strip()
        email      = request.form['email'].strip()
        username   = request.form['username'].strip()
        first      = request.form['first_name'].strip()
        last       = request.form['last_name'].strip()
        address    = request.form['address'].strip()
        d_num      = request.form['d_num']
        password   = request.form['password']
        confirm    = request.form['confirm_password']
        faculty_role = request.form['faculty_role']

        if password != confirm:
            return render_template('REGS-addfaculty.html', error="Passwords do not match")
        if not re.fullmatch(r'\d{8}', uid):
            return render_template('REGS-addfaculty.html', error="UID must be exactly 8 digits")
        if '@example.edu' not in email:
            return render_template('REGS-addfaculty.html', error="Email must be @example.edu")
        
        conn = get_db_connection()

        for col in ('uid','email','username'):
            if conn.execute(f"SELECT 1 FROM users WHERE {col}=?", (locals()[col],)).fetchone():
                conn.close()
                return render_template('REGS-addfaculty.html', error=f"{col.capitalize()} already in use")

        conn.execute("""
            INSERT INTO users
            (uid, email, username, password, user_type, first_name, last_name, address)
            VALUES (?, ?, ?, ?, 3, ?, ?, ?)
        """, (uid, email, username, password, first, last, address))

        # Set flags based on the selected role
        is_reviewer = 1 if faculty_role in ['reviewer', 'cac'] else 0
        is_cac = 1 if faculty_role == 'cac' else 0

        # new insert into faculty
        conn.execute("""
            INSERT INTO faculty(uid, d_num, is_reviewer, is_cac)
            VALUES (?, ?, ?, ?)
        """, (uid, d_num, is_reviewer, is_cac))

        # insert into faculty
        #conn.execute("INSERT INTO faculty(uid,d_num) VALUES (?,?)", (uid, d_num))
        conn.commit()
        conn.close()
        return redirect(url_for('addfaculty', success="Faculty added!"))

    # GET
    # pull department list for dropdown
    conn = get_db_connection()
    depts = conn.execute("SELECT d_num, d_name FROM department").fetchall()
    conn.close()
    return render_template('REGS-addfaculty.html',
                           success=request.args.get('success'),
                           departments=depts)


@app.route('/addstudents', methods=['GET','POST'])
def addstudents():
    conn = get_db_connection()
    departments = conn.execute("SELECT d_num, d_name FROM department").fetchall()
    faculty_list = conn.execute("""
        SELECT f.uid, u.first_name, u.last_name
        FROM faculty f
        JOIN users u ON f.uid = u.uid
    """).fetchall()

    if request.method == 'POST':
        uid       = request.form['uid'].strip()
        email     = request.form['email'].strip()
        username  = request.form['username'].strip()
        first     = request.form['first_name'].strip()
        last      = request.form['last_name'].strip()
        address   = request.form['address'].strip()
        program   = request.form['program']
        d_num     = request.form['d_num']
        advisor   = request.form.get('advisor_uid') or None
        password  = request.form['password']
        confirm   = request.form['confirm_password']

        error = None
        if password != confirm:
            error = "Passwords do not match"
        elif not re.fullmatch(r'\d{8}', uid):
            error = "UID must be exactly 8 digits"
        elif '@example.edu' not in email:
            error = "Email must be @example.edu"
        else:
            for col in ('uid','email','username'):
                if conn.execute(f"SELECT 1 FROM users WHERE {col}=?", (locals()[col],)).fetchone():
                    error = f"{col.capitalize()} already in use"
                    break

        if error:
            conn.close()
            return render_template(
                'REGS-addstudents.html',
                error=error,
                departments=departments,
                faculty_list=faculty_list,
                form_data=request.form
            )

        conn.execute("""
          INSERT INTO users
            (uid, email, username, password, user_type,
             first_name, last_name, address)
          VALUES (?, ?, ?, ?, 2, ?, ?, ?)
        """, (uid,email,username,password,first,last,address))

        conn.execute("""
          INSERT INTO grad_student
            (uid, advisor_uid, d_num, program)
          VALUES (?, ?, ?, ?)
        """, (uid, advisor, d_num, program))

        conn.commit()
        conn.close()
        return redirect(url_for('addstudents', success="Grad student added!"))

    conn.close()
    return render_template(
        'REGS-addstudents.html',
        success=request.args.get('success'),
        departments=departments,
        faculty_list=faculty_list
    )



@app.route('/addgs', methods=['GET','POST'])
def addgs():
    if request.method == 'POST':
        uid      = request.form['uid'].strip()
        email    = request.form['email'].strip()
        username = request.form['username'].strip()
        first    = request.form['first_name'].strip()
        last     = request.form['last_name'].strip()
        address = request.form['address'].strip()
        password = request.form['password']
        confirm  = request.form['confirm_password']

        if password != confirm:
            return render_template('REGS-addgs.html', error="Passwords do not match")
        if not re.fullmatch(r'\d{8}', uid):
            return render_template('REGS-addgs.html', error="UID must be exactly 8 digits")
        if '@example.edu' not in email:
            return render_template('REGS-addgs.html', error="Email must be @example.edu")
        
        conn = get_db_connection()
        # uniqueness…
        for col in ('uid','email','username'):
            if conn.execute(f"SELECT 1 FROM users WHERE {col}=?", (locals()[col],)).fetchone():
                conn.close()
                return render_template('REGS-addgs.html', error=f"{col.capitalize()} already in use")
            
        conn.execute("""
            INSERT INTO users
            (uid, email, username, password, user_type, first_name, last_name, address)
            VALUES (?, ?, ?, ?, 5, ?, ?, ?)
        """, (uid, email, username, password, first, last, address))
        
        conn.execute("INSERT INTO grad_secretary(uid) VALUES (?)", (uid,))
        conn.commit()
        conn.close()
        return redirect(url_for('addgs', success="Grad Secretary added!"))

    conn = get_db_connection()
    depts = conn.execute("SELECT d_num, d_name FROM department").fetchall()
    conn.close()
    return render_template('REGS-addgs.html',
                           success=request.args.get('success'),
                           departments=depts)

@app.route('/addadmin', methods=['GET', 'POST'])
def addadmin():
    if request.method == 'POST':
        uid  = request.form['uid'].strip()
        email = request.form['email'].strip()
        username = request.form['username'].strip()
        first = request.form['first_name'].strip()
        last  = request.form['last_name'].strip()
        address   = request.form['address'].strip()
        password = request.form['password']
        confirm  = request.form['confirm_password']
        address  = request.form.get('address','').strip()

        # validations…
        if password != confirm:
            return render_template('REGS-addadmin.html', error="Passwords do not match")
        if not re.fullmatch(r'\d{8}', uid):
            return render_template('REGS-addadmin.html', error="UID must be exactly 8 digits")
        if '@example.edu' not in email:
            return render_template('REGS-addadmin.html', error="Email must be @example.edu")

        conn = get_db_connection()
        # uniqueness checks…
        for col in ('uid','email','username'):
            if conn.execute(f"SELECT 1 FROM users WHERE {col}=?", (locals()[col],)).fetchone():
                conn.close()
                return render_template('REGS-addadmin.html', error=f"{col.capitalize()} already in use")

        # Insert into users (now 'password' not 'password_hash')
        conn.execute("""
            INSERT INTO users
            (uid, email, username, password, user_type, first_name, last_name, address)
            VALUES (?, ?, ?, ?, 5, ?, ?, ?)
        """, (uid, email, username, password, first, last, address))
        # Then into admin table
        conn.execute("INSERT INTO admin(uid) VALUES (?)", (uid,))
        conn.commit()
        conn.close()

        return redirect(url_for('addadmin', success="Admin created!"))

    return render_template('REGS-addadmin.html',
                           success=request.args.get('success'))

@app.route('/applicant/dashboard')
def applicant_dashboard():
    if 'uid' not in session or session.get('role') != 'applicant':
        return redirect(url_for('login'))

    conn = get_db_connection()

    applicant = conn.execute("""
        SELECT 
            u.first_name || ' ' || u.last_name AS name,
            u.address,
            a.*
        FROM applicant a
        JOIN users u ON a.uid = u.uid
        WHERE a.uid = ?
    """, (session['uid'],)).fetchone()

    letters = conn.execute(
        "SELECT * FROM recommendation_letter WHERE applicant_uid = ?", 
        (session['uid'],)
    ).fetchall()

    conn.close()

    return render_template('applicant_dashboard.html', applicant=applicant, recommendation_letters=letters)

@app.route('/applicant/request_recommendation', methods=['POST'])
def request_recommendation():
    if 'uid' not in session or session.get('role') != 'applicant':
        return redirect(url_for('login'))

    writer_name = request.form.get('writer_name')
    writer_email = request.form.get('writer_email')
    writer_title = request.form.get('writer_title')
    institution_name = request.form.get('institution_name')

    if not all([writer_name, writer_email, writer_title, institution_name]):
        flash('Please provide all required information for the letter writer.', 'danger')
        return redirect(url_for('applicant_dashboard'))

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO recommendation_letter (applicant_uid, writer_name, writer_email, writer_title, institution_name)
        VALUES (?, ?, ?, ?, ?)
    """, (session['uid'], writer_name, writer_email, writer_title, institution_name))
    letter_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    submission_url = url_for('submit_letter', letter_id=letter_id, _external=True)
    flash(f'Recommendation letter request has been created. Share this link with your letter writer: {submission_url}', 'success')

    return redirect(url_for('applicant_dashboard'))

@app.route('/applicant/submit_letter/<int:letter_id>', methods=['GET', 'POST'])
def submit_letter(letter_id):
    conn = get_db_connection()
    letter = conn.execute("SELECT * FROM recommendation_letter WHERE id = ?", (letter_id,)).fetchone()

    # Fetch applicant info if needed for display
    applicant = None
    if letter:
        applicant = conn.execute("SELECT * FROM users WHERE uid = ?", (letter['applicant_uid'],)).fetchone()

    if request.method == 'POST':
        letter_content = request.form.get('letter_content')
        if not letter_content:
            flash('Please provide the letter content.', 'danger')
            return redirect(url_for('submit_letter', letter_id=letter_id))

        conn.execute("""
            UPDATE recommendation_letter
            SET letter_content = ?, is_submitted = 1, submission_date = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (letter_content, letter_id))
        conn.commit()
        conn.close()
        flash('Thank you for submitting the recommendation letter!', 'success')
        return redirect(url_for('submit_letter', letter_id=letter_id))

    conn.close()
    return render_template('submit_letter.html', letter=letter, applicant=applicant)


@app.route('/applicant/register', methods=['GET', 'POST'])
def applicant_register():
    form_data = {}
    if request.method == 'POST':
        name = request.form.get('name')
        ssn = request.form.get('ssn')
        address = request.form.get('address')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        semester = request.form.get('semester', 'Fall 2024')
        degree_sought = request.form.get('degree_sought', 'MS')
        gre_verbal = request.form.get('gre_verbal')
        gre_quant = request.form.get('gre_quant')
        gre_year = request.form.get('gre_year')
        work_experience = request.form.get('work_experience')
        areas_of_interest = request.form.get('areas_of_interest')

        subjects = request.form.getlist('gre_subject_name[]')
        scores = request.form.getlist('gre_subject_score[]')
        years = request.form.getlist('gre_subject_year[]')
        gre_subjects = [{"subject": s, "score": sc, "year": y} for s, sc, y in zip(subjects, scores, years) if s or sc]

        degree_types = request.form.getlist('degree_type[]')
        universities = request.form.getlist('university[]')
        degree_years = request.form.getlist('degree_year[]')
        gpas = request.form.getlist('gpa[]')
        prior_degrees = [{"degree_type": dt, "university": u, "year": y, "gpa": g} for dt, u, y, g in zip(degree_types, universities, degree_years, gpas) if dt or u or y or g]

        # Inline SSN validation
        if not re.match(r'^\d{3}-\d{2}-\d{4}$', ssn):
            return render_template('applicant_register.html', error='SSN must be in the format XXX-XX-XXXX.', form_data=form_data)
        if password != confirm_password:
            return render_template('applicant_register.html', error='Passwords do not match.', form_data=form_data)

        conn = get_db_connection()
        existing_ssn = conn.execute("SELECT 1 FROM applicant WHERE ssn = ?", (ssn,)).fetchone()
        if existing_ssn:
            return render_template('applicant_register.html', error='This SSN is already registered.', form_data=form_data)

        if degree_sought == 'PhD' and (not gre_verbal or not gre_quant or not gre_year):
            return render_template('applicant_register.html', error='GRE scores are required for PhD applicants.', form_data=form_data)

        # Inline UID generation
        existing_uids = {row['uid'] for row in conn.execute("SELECT uid FROM users").fetchall()}
        while True:
            uid = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            if uid not in existing_uids:
                break

        conn.execute("""
            INSERT INTO users (uid, email, username, password, user_type, first_name, last_name, address)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """, (uid, f"{uid}@email.com", uid, password, name.split()[0], name.split()[-1], address))

        conn.execute("""
            INSERT INTO applicant (uid, semester, ssn, degree_sought, gre_verbal, gre_quant, gre_year, work_experience, areas_of_interest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, semester, ssn, degree_sought, gre_verbal, gre_quant, gre_year, work_experience, areas_of_interest))

        for g in gre_subjects:
            if g['subject'] and g['score']:
                conn.execute("""
                    INSERT INTO gre_subject (applicant_uid, subject, score, year)
                    VALUES (?, ?, ?, ?)
                """, (uid, g['subject'], g['score'], g['year'] or None))

        for d in prior_degrees:
            if d['degree_type'] and d['university'] and d['year'] and d['gpa']:
                conn.execute("""
                    INSERT INTO prior_degree (applicant_uid, degree_type, year, gpa, university)
                    VALUES (?, ?, ?, ?, ?)
                """, (uid, d['degree_type'], d['year'], d['gpa'], d['university']))

        conn.commit()
        conn.close()

        session['uid'] = uid
        session['name'] = name
        session['role'] = 'applicant'
        flash('Registration successful! Your UID is: ' + uid + '. You are now logged in.')
        return redirect(url_for('applicant_dashboard'))

    return render_template('applicant_register.html', form_data=form_data)

#helper function for faculty apps handling
def get_faculty_role(uid):
    conn = get_db_connection()
    role_row = conn.execute("""
        SELECT
            CASE
                WHEN EXISTS (SELECT 1 FROM admin WHERE uid = ?) THEN 'admin'
                WHEN EXISTS (SELECT 1 FROM grad_secretary WHERE uid = ?) THEN 'gs'
                WHEN EXISTS (SELECT 1 FROM faculty WHERE uid = ? AND is_cac = 1) THEN 'cac'
                WHEN EXISTS (SELECT 1 FROM faculty WHERE uid = ? AND is_reviewer = 1) THEN 'reviewer'
                ELSE 'faculty'
            END AS role
    """, (uid, uid, uid, uid)).fetchone()
    conn.close()
    return role_row['role'] if role_row else 'faculty'

#helper function for faculty dash
import datetime
def parse_timestamp(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


@app.route('/faculty/dashboard')
def faculty_dashboard():
    conn = get_db_connection()
    search = request.args.get('search')
    gs_search_semester = request.args.get('gs_semester')
    gs_search_year = request.args.get('gs_year')
    gs_search_degree = request.args.get('gs_degree')

    # Handle GS stats search
    gs_stats = None
    if session.get('role') == 'gs':
        semester = request.args.get('gs_semester')
        year = request.args.get('gs_year')
        degree = request.args.get('gs_degree')

        if semester or year or degree:
            query = """
                SELECT
                    COUNT(*) AS total_applicants,
                    SUM(CASE WHEN status = 'admitted' THEN 1 ELSE 0 END) AS total_admitted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS total_rejected,
                    AVG(CASE WHEN status = 'admitted' THEN gre_verbal ELSE NULL END) AS avg_verbal,
                    AVG(CASE WHEN status = 'admitted' THEN gre_quant ELSE NULL END) AS avg_quant,
                    AVG(CASE WHEN status = 'admitted' THEN (gre_verbal + gre_quant) ELSE NULL END) AS avg_total
                FROM applicant
                WHERE 1=1
            """
            params = []

            if semester:
                query += " AND semester = ?"
                params.append(semester)
            if year:
                query += " AND CAST(SUBSTR(semester, -4) AS INTEGER) = ?"
                params.append(year)
            if degree:
                query += " AND degree_sought = ?"
                params.append(degree)

            gs_stats = conn.execute(query, params).fetchone()

    base_query = """
        SELECT a.*, 
            u.created_at,
            u.first_name || ' ' || u.last_name AS name,
            COUNT(DISTINCT rl.id) FILTER (WHERE rl.is_submitted = 1) AS submitted_letters,
            COUNT(DISTINCT rl.id) AS total_letters,
            COUNT(DISTINCT r.id) AS submitted_reviews,
            ROUND(AVG(r.rating), 2) AS average_rating
        FROM applicant a
        JOIN users u ON a.uid = u.uid
        LEFT JOIN recommendation_letter rl ON rl.applicant_uid = a.uid
        LEFT JOIN review r ON r.applicant_uid = a.uid
    """

    applicants_query = base_query
    filters = []
    params = []

    if search:
        filters.append("(u.last_name LIKE ? OR a.uid = ?)")
        params.extend([f"%{search}%", search])

    # Only GS can search by semester/year/degree
    if session.get('role') == 'gs':
        if gs_search_semester:
            filters.append("a.semester LIKE ?")
            params.append(f"%{gs_search_semester}%")
        if gs_search_year:
            filters.append("CAST(SUBSTR(a.semester, -4) AS INTEGER) = ?")
            params.append(gs_search_year)
        if gs_search_degree:
            filters.append("a.degree_sought = ?")
            params.append(gs_search_degree)

    if filters:
        applicants_query += " WHERE " + " AND ".join(filters)

    applicants_query += " GROUP BY a.uid"

    raw_applicants = conn.execute(applicants_query, tuple(params)).fetchall()

    applicants = []
    if session.get('role') == 'reviewer':
        reviewed = conn.execute("SELECT applicant_uid FROM review WHERE reviewer_id = ?", (session['uid'],)).fetchall()
        reviewed_uids = {row['applicant_uid'] for row in reviewed}
        for row in raw_applicants:
            if row['status'] == 'under review' and row['uid'] not in reviewed_uids:
                row_dict = dict(row)
                row_dict['created_at'] = parse_timestamp(row['created_at'])
                applicants.append((row_dict, row['submitted_letters'], row['total_letters'], row['submitted_reviews']))
    else:
        for row in raw_applicants:
            row_dict = dict(row)
            row_dict['created_at'] = parse_timestamp(row['created_at'])
            applicants.append((row_dict, row['submitted_letters'], row['total_letters'], row['submitted_reviews']))

    decided_applications = conn.execute("""
        SELECT a.*, u.first_name || ' ' || u.last_name AS name, u.created_at, u.updated_at
        FROM applicant a
        JOIN users u ON a.uid = u.uid
        WHERE a.status IN ('admitted', 'rejected')
        ORDER BY a.uid DESC
    """).fetchall()

    decided_applications = [dict(row) for row in decided_applications]
    for d in decided_applications:
        d['updated_at'] = parse_timestamp(d['updated_at'])

    conn.close()
    return render_template('faculty_dashboard.html', 
                           applicants=applicants, 
                           role=session.get('role'), 
                           decided_applications=decided_applications,
                           gs_stats=gs_stats)



@app.route('/faculty/update_transcript/<uid>', methods=['POST'])
def update_transcript(uid):
    if 'uid' not in session or session.get('role') not in ['admin', 'gs']:
        flash('You do not have permission to update transcript status.', 'error')
        return redirect(url_for('faculty_dashboard'))

    new_status = request.form.get('transcript_status') == 'true'

    conn = get_db_connection()
    conn.execute("UPDATE applicant SET transcript_received = ? WHERE uid = ?", (new_status, uid))
    conn.commit()
    conn.close()

    flash('Transcript status updated.', 'success')
    return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/final_decisions/<uid>', methods=['GET', 'POST'])
def final_decisions(uid):
    if 'uid' not in session or session.get('role') not in ['admin', 'cac', 'gs']:
        return redirect(url_for('login'))

    conn = get_db_connection()
    applicant = conn.execute("""
        SELECT a.*, u.first_name || ' ' || u.last_name AS name
        FROM applicant a
        JOIN users u ON a.uid = u.uid
        WHERE a.uid = ?
    """, (uid,)).fetchone()

    if not applicant:
        conn.close()
        flash('Applicant not found.', 'error')
        return redirect(url_for('faculty_dashboard'))

    recommendation_letters = conn.execute(
        "SELECT * FROM recommendation_letter WHERE applicant_uid = ?", (uid,)
    ).fetchall()

    if applicant['status'] != 'under review':
        conn.close()
        flash('This applicant is not ready for final decision.', 'error')
        return redirect(url_for('faculty_dashboard'))

    if request.method == 'POST':
        decision = request.form.get('decision')
        if decision:
            status = 'admitted' if decision in ['Admit', 'Admit with Aid'] else 'rejected'
            conn.execute("UPDATE applicant SET status = ? WHERE uid = ?", (status, uid))
            conn.commit()
            conn.close()
            flash(f'Decision "{decision}" submitted for {applicant["uid"]}.', 'success')
            return redirect(url_for('faculty_dashboard'))
        else:
            flash('Missing selection.', 'warning')

    reviews = conn.execute("""
        SELECT r.*, 
            u.first_name || ' ' || u.last_name AS reviewer_name,
            a.first_name || ' ' || a.last_name AS advisor_name
        FROM review r
        JOIN users u ON r.reviewer_id = u.uid
        JOIN users a ON r.recommended_advisor = a.uid
        WHERE r.applicant_uid = ?
    """, (uid,)).fetchall()

    # Attach reviews and advisors properly
    applicant = dict(applicant)
    applicant['reviews'] = []
    for r in reviews:
        review = dict(r)
        try:
            review['submitted_at'] = datetime.strptime(r['submitted_at'], '%Y-%m-%d %H:%M:%S')
        except:
            review['submitted_at'] = None
        review['reviewer'] = {'name': r['reviewer_name']}
        review['advisor'] = {'name': r['advisor_name']}
        applicant['reviews'].append(review)
    
    prior_degrees = conn.execute("SELECT * FROM prior_degree WHERE applicant_uid = ?", (uid,)).fetchall()

    conn.close()
    return render_template('final_decisions.html', applicant=applicant, role=session.get('role'), recommendation_letters=recommendation_letters,prior_degrees=prior_degrees)

@app.route('/faculty/view_decided_applicant/<uid>')
def view_decided_applicant(uid):
    if 'uid' not in session or session.get('role') not in ['admin', 'gs', 'reviewer', 'cac']:
        return redirect(url_for('login'))

    conn = get_db_connection()

    applicant = conn.execute(
        "SELECT * FROM applicant WHERE uid = ?", (uid,)
    ).fetchone()

    gre_subjects = conn.execute(
        "SELECT * FROM gre_subject WHERE applicant_uid = ?", (uid,)
    ).fetchall()

    prior_degrees = conn.execute(
        "SELECT * FROM prior_degree WHERE applicant_uid = ?", (uid,)
    ).fetchall()

    recommendation_letters = conn.execute(
        "SELECT * FROM recommendation_letter WHERE applicant_uid = ?", (uid,)
    ).fetchall()
    name = conn.execute("""
        SELECT first_name || ' ' || last_name AS full_name
        FROM users
        WHERE uid = ?
    """, (uid,)).fetchone()

    conn.close()

    return render_template('view_decided_applicant.html', applicant=applicant, role=session.get('role'),
                           gre_subjects=gre_subjects, prior_degrees=prior_degrees, recommendation_letters=recommendation_letters,name = name['full_name'])


@app.route('/faculty/review/<uid>', methods=['GET', 'POST'])
def review_applicant(uid):
    if 'uid' not in session or session.get('role') not in ['admin', 'reviewer', 'cac']:
        return redirect(url_for('login'))

    conn = get_db_connection()
    applicant = conn.execute("""
        SELECT a.*, u.first_name || ' ' || u.last_name AS full_name
        FROM applicant a JOIN users u ON a.uid = u.uid WHERE a.uid = ?
    """, (uid,)).fetchone()

    if not applicant:
        conn.close()
        abort(404)

    advisors = conn.execute("""
        SELECT f.uid, u.first_name || ' ' || u.last_name AS name
        FROM faculty f JOIN users u ON f.uid = u.uid WHERE f.is_reviewer = 1
    """).fetchall()

    recommendation_letters = conn.execute("""
        SELECT rl.*, (
            SELECT COUNT(*) FROM recommendation_letter_review
            WHERE letter_id = rl.id AND reviewer_id = ?
        ) AS already_reviewed
        FROM recommendation_letter rl
        WHERE applicant_uid = ?
    """, (session['uid'], uid)).fetchall()

    if request.method == 'POST':
        gas_rating = request.form.get('gas_rating')
        deficiency_courses = request.form.get('deficiency_courses')
        reject_reasons = request.form.getlist('reject_reason')
        gas_comments = request.form.get('gas_comments')
        advisor_id = request.form.get('recommended_advisor')

        if not all([gas_rating, gas_comments, advisor_id]):
            flash('Please complete all required GAS review fields.', 'error')
            conn.close()
            return redirect(request.url)

        try:
            conn.execute("""
                INSERT INTO review (applicant_uid, reviewer_id, rating, deficiency_courses, reject_reasons, comment, recommended_advisor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                uid,
                session['uid'],
                int(gas_rating),
                deficiency_courses,
                ','.join(reject_reasons),
                gas_comments,
                advisor_id
            ))

            conn.execute("UPDATE applicant SET status = ? WHERE uid = ?", ('under review', uid))
            conn.commit()
            flash('GAS review submitted successfully.', 'success')
            return redirect(url_for('faculty_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Error during GAS review submission: {e}', 'error')
        finally:
            conn.close()

    conn.close()
    return render_template('review_applicant.html',
                           applicant=applicant,
                           advisors=advisors,
                           recommendation_letters=recommendation_letters,
                           role=session.get('role'))




@app.route('/faculty/review_letter/<int:letter_id>', methods=['POST'])
def review_letter(letter_id):
    if 'uid' not in session or session.get('role') not in ['admin', 'reviewer', 'cac']:
        return redirect(url_for('login'))

    conn = get_db_connection()
    letter = conn.execute("SELECT * FROM recommendation_letter WHERE id = ?", (letter_id,)).fetchone()

    submit_by_mail = request.form.get('submit_by_mail')

    if not letter:
        conn.close()
        flash('Letter not found.', 'warning')
        return redirect(url_for('faculty_dashboard'))

    if not letter['is_submitted'] and not submit_by_mail:
        conn.close()
        flash('Cannot review a letter that has not been submitted.', 'warning')
        return redirect(url_for('review_applicant', uid=letter['applicant_uid']))

    # If it was marked submitted by mail, update the flag
    if submit_by_mail and not letter['is_submitted']:
        conn.execute("UPDATE recommendation_letter SET is_submitted = 1 WHERE id = ?", (letter_id,))


    existing_review = conn.execute("""
        SELECT * FROM recommendation_letter_review
        WHERE letter_id = ? AND reviewer_id = ?
    """, (letter_id, session['uid'])).fetchone()

    rating = request.form.get('rating')
    is_generic = request.form.get('is_generic')
    is_credible = request.form.get('is_credible')

    if not all([rating, is_generic, is_credible]):
        conn.close()
        flash('All fields are required for the review.', 'error')
        return redirect(url_for('review_applicant', uid=letter['applicant_uid']))

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")
        if is_generic not in ['Y', 'N'] or is_credible not in ['Y', 'N']:
            raise ValueError("Invalid values for generic or credible fields")

        if existing_review:
            conn.execute("""
                UPDATE recommendation_letter_review
                SET rating = ?, is_generic = ?, is_credible = ?, updated_at = CURRENT_TIMESTAMP
                WHERE letter_id = ? AND reviewer_id = ?
            """, (rating, is_generic, is_credible, letter_id, session['uid']))
            flash('Letter review updated successfully.', 'success')
        else:
            conn.execute("""
                INSERT INTO recommendation_letter_review (letter_id, reviewer_id, rating, is_generic, is_credible)
                VALUES (?, ?, ?, ?, ?)
            """, (letter_id, session['uid'], rating, is_generic, is_credible))
            flash('Letter review submitted successfully.', 'success')

        conn.commit()
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'error')
    except Exception:
        conn.rollback()
        flash('An error occurred while submitting the review. Please try again.', 'error')
    finally:
        conn.close()

    return redirect(url_for('review_applicant', uid=letter['applicant_uid']))

@app.route('/gs/gsAlumniList', methods=['GET', 'POST'])
def gsAlumniList():
    if 'uid' not in session or session.get('user_type') != 5:
        flash('Ur not a grad secretary!', 'error')
        return redirect(url_for('login'))
    
    semester = request.form.get('semester','').strip()
    year     = request.form.get('year','').strip()
    program  = request.form.get('program','').strip()
    results = []
    
    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    query = "SELECT a.uid, u.first_name || ' ' || u.last_name AS name, u.email, a.graduation_semester, a.degree FROM alumni a JOIN users u ON u.uid = a.uid"

    filters = []
    restrictions  = []
    if semester:
        filters.append("a.graduation_semester LIKE ?")
        restrictions.append(f"{semester}%")
    if year:
        filters.append("a.graduation_semester LIKE ?")
        restrictions.append(f"%{year}%")
    if program:
        filters.append("a.degree LIKE ?")
        restrictions.append(f"%{program}%")

    # if we have any filters, join them with AND
    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY a.graduation_semester, a.uid"

    connection = sqlite3.connect("phase-2.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    results = cur.execute(query, restrictions).fetchall()
    connection.close()

    return render_template('gsAlumniList.html', results=results, semester=semester, year=year, program=program)

@app.route('/gs/graduating', methods=['GET'])
def search_graduating_students():
    if 'uid' not in session or session.get('user_type') != 5:
        return redirect(url_for('login'))
    
    query = request.args.get('query', '').strip()

    sql = """
        SELECT u.uid,
               u.first_name AS fname,
               u.last_name  AS lname,
               g.program,
               g.gpa,
               g.advisor_uid
        FROM users u
        JOIN grad_student g ON u.uid = g.uid
        WHERE g.graduation_requested = 1
    """
    params = []

    if query:
        sql += " AND (u.first_name LIKE ? OR u.last_name LIKE ? OR u.uid LIKE ?)"
        q = f"%{query}%"
        params += [q, q, q]

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(sql, params)
    students = cur.fetchall()

    cur.execute(sql, params)
    students = cur.fetchall()

    cur.execute("""
        SELECT u.uid, u.first_name AS fname, u.last_name AS lname
        FROM users u
        JOIN faculty f ON u.uid = f.uid
        WHERE f.is_advisor = 1
    """)
    advisors = cur.fetchall()
    assignedAdvisor = {a['uid']: f"{a['fname']} {a['lname']}" for a in advisors}

    conn.close()
    return render_template(
        'gsGraduating.html',
        students=students,
        assignedAdvisor=assignedAdvisor,
        query=query
    )

from datetime import date

@app.route('/submit_payment', methods=['GET', 'POST'])
def submit_payment():
    if 'uid' not in session or session.get('role') != 'applicant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    applicant = conn.execute("SELECT * FROM applicant WHERE uid = ?", (session['uid'],)).fetchone()

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        if payment_method == 'online':
            # Simulate payment form fields being filled
            card_number = request.form.get('card_number')
            expiration = request.form.get('expiration')
            cvv = request.form.get('cvv')

            if card_number and expiration and cvv:
                conn.execute("UPDATE applicant SET payment_method = ?, payment_submitted = 1 WHERE uid = ?", (payment_method, session['uid']))
                conn.commit()
                flash('Payment submitted successfully!', 'success')
                conn.close()
                return redirect(url_for('applicant_dashboard'))
            else:
                flash('Please fill in all payment fields.', 'danger')

        elif payment_method == 'check':
            conn.execute("UPDATE applicant SET payment_method = ?, payment_submitted = 0 WHERE uid = ?", (payment_method, session['uid']))
            conn.commit()
            flash('Please mail your check. GS will confirm once received.', 'info')
            conn.close()
            return redirect(url_for('applicant_dashboard'))

    conn.close()
    return render_template('submit_payment.html', applicant=applicant)

# GS confirms check payment
@app.route('/confirm_check/<uid>', methods=['POST'])
def confirm_check(uid):
    if 'uid' not in session or session.get('role') != 'gs':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("UPDATE applicant SET payment_submitted = 1 WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()
    flash('Check payment confirmed.', 'success')
    return redirect(url_for('faculty_dashboard'))

# GS matriculates a student
@app.route('/matriculate_student/<uid>', methods=['POST'])
def matriculate_student(uid):
    if 'uid' not in session or session.get('role') != 'gs':
        return redirect(url_for('login'))

    conn = get_db_connection()
    applicant = conn.execute("SELECT * FROM applicant WHERE uid = ?", (uid,)).fetchone()
    if not applicant:
        conn.close()
        flash('Applicant not found.', 'error')
        return redirect(url_for('faculty_dashboard'))

    # Insert into grad_student
    d_num = 1  # Set default department to CS (or dynamically pull if you want)
    conn.execute("""
        INSERT INTO grad_student (uid, d_num, program, matriculation_date)
        VALUES (?, ?, ?, ?)
    """, (uid, d_num, applicant['degree_sought'] + " in Computer Science", date.today()))

    conn.execute("""
        UPDATE users
           SET user_type = 2
         WHERE uid = ?
    """, (uid,))
    
    # Remove from applicant table
    conn.execute("""
        DELETE FROM applicant WHERE uid = ?
    """, (uid,))

    conn.commit()
    conn.close()
    flash('Student matriculated successfully!', 'success')
    return redirect(url_for('faculty_dashboard'))


@app.route('/applicant/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'uid' not in session:
        return redirect(url_for('login'))

    uid = session['uid']
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone()

    # Check if the user is also an applicant
    applicant = conn.execute("SELECT * FROM applicant WHERE uid = ?", (uid,)).fetchone()

    if request.method == 'POST':
        # Update basic user information
        email = request.form['email'].strip()
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        address = request.form['address'].strip()

        conn.execute("""
            UPDATE users
            SET email = ?, first_name = ?, last_name = ?, address = ?
            WHERE uid = ?
        """, (email, first_name, last_name, address, uid))

        # Update applicant academic info if applicable
        if applicant:
            gre_verbal = request.form.get('gre_verbal')
            gre_quant = request.form.get('gre_quant')
            gre_year = request.form.get('gre_year')
            work_experience = request.form.get('work_experience')
            areas_of_interest = request.form.get('areas_of_interest')

            conn.execute("""
                UPDATE applicant
                SET gre_verbal = ?, gre_quant = ?, gre_year = ?, work_experience = ?, areas_of_interest = ?
                WHERE uid = ?
            """, (gre_verbal or None, gre_quant or None, gre_year or None, work_experience, areas_of_interest, uid))

        conn.commit()
        conn.close()
        flash('Information updated successfully.', 'success')
        return redirect(url_for('home'))

    conn.close()
    return render_template('applicant_edit_info.html', user=user, applicant=applicant)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

