from flask import Flask, render_template, request, redirect, url_for, session,send_from_directory,flash
import mysql.connector
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "jobsecret"

# ================= DATABASE =================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="job_search_system"
)

cursor = db.cursor(dictionary=True)

# ================= UPLOAD FOLDER =================
app.config['UPLOAD_FOLDER'] = os.path.join('static/resumes')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])



# ================= HOME =================
@app.route('/')
def home():
    return render_template("index.html")

# ================= REGISTER =================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        skills = request.form['skills']
        cursor.execute("SELECT * FROM users WHERE email=%s",(email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return "Email already registered! Please login"

        cursor.execute(
            "INSERT INTO users(name,email,password,phone,skills) VALUES(%s,%s,%s,%s,%s)",
            (name,email,password,phone,skills)
        )
        db.commit()

        return redirect(url_for('login'))

    return render_template("register.html")

# ================= LOGIN =================
@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        email = request.form.get("email")
        password = request.form.get("password")

        try:

            cur = db.cursor(dictionary=True)

            cur.execute("""
            SELECT * FROM users
            WHERE email=%s AND password=%s
            """,(email,password))

            user = cur.fetchone()

            if user:

                # ⭐ Store session (VERY IMPORTANT)
                session['user_email'] = user['email']

                return redirect(url_for('dashboard'))

            else:
                return "Invalid Login"

        except Exception as e:
            print("Login Error:", e)
            return "Internal Server Error"

    return render_template("login.html")




# ================= FORGOT PASSWORD =================
@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':

        email = request.form['email']
        new_password = request.form['password']

        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password,email)
        )

        db.commit()

        return redirect(url_for('login'))

    return render_template("forgot_password.html")

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search')

    # ⭐ My Applications (Optional)
    cursor.execute("""
    SELECT * FROM applications
    WHERE email=%s
    """,(session['user_email'],))

    myapplications = cursor.fetchall()

    # ⭐ Recommended Jobs (Safe Logic)
    recommended_jobs = []

    try:

        cursor.execute("""
        SELECT skills FROM users
        WHERE email=%s
        """,(session['user_email'],))

        user = cursor.fetchone()

        if user and user['skills']:

            skills_list = user['skills'].split(",")

            for skill in skills_list:

                cursor.execute("""
                SELECT * FROM jobs
                WHERE title LIKE %s
                OR description LIKE %s
                OR category LIKE %s
                """,(f"%{skill.strip()}%",)*3)

                for job in cursor.fetchall():
                    if job not in recommended_jobs:
                        recommended_jobs.append(job)

    except:
        pass

    # ⭐ All Jobs + Search
    if search:

        cursor.execute("""
        SELECT * FROM jobs
        WHERE title LIKE %s
        OR company LIKE %s
        OR location LIKE %s
        """,(f"%{search}%",f"%{search}%",f"%{search}%"))

    else:

        cursor.execute("SELECT * FROM jobs")

    jobs = cursor.fetchall()

    return render_template(
        "dashboard.html",
        jobs=jobs,
        myapplications=myapplications,
        recommended_jobs=recommended_jobs
    )



# ================= APPLY APPLICATION =================
@app.route('/applications_form/<int:job_id>', methods=['GET','POST'])
def applications_form(job_id):

    if 'user_email' not in session:
        return redirect(url_for('login'))

    # Get job details
    cursor.execute("SELECT * FROM jobs WHERE id=%s",(job_id,))
    job = cursor.fetchone()

    if request.method == 'POST':

        name = request.form.get("name")
        email = request.form.get("email")
        phone_no = request.form.get("phone_no")
        need_of_job=request.form.get("need_of_job")
        company=request.form.get('company')
        
        

        resume = request.files['resume']
        filename = resume.filename

        resume.save(
            os.path.join(app.config['UPLOAD_FOLDER'], filename)
        )
        cursor.execute("SELECT company FROM jobs WHERE id=%s",(job_id,))
        job=cursor.fetchone()
        company=job['company']

        cursor.execute("""
        INSERT INTO applications
        (name,email,phone_no,resume,need_of_job,status,company)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """,(name,email,phone_no,filename,need_of_job,"Pending",company))

        db.commit()

        return redirect(url_for('my_applications'))

    return render_template("applications_form.html", job=job)

        
        

# ================= MY APPLICATIONS =================
@app.route('/my_applications')
def my_applications():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    cursor.execute(
        "SELECT * FROM applications WHERE email=%s",
        (session['user_email'],)
    )

    data = cursor.fetchall()

    return render_template("my_applications.html", data=data)
@app.route('/delete_application/<int:id>')
def delete_application(id):

    if 'user_email' not in session:
        return redirect(url_for('login'))

    cursor.execute(
        "DELETE FROM applications WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect(url_for('my_applications'))
# ================= USER LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ================= ADMIN LOGIN =================
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username,password)
        )

        admin = cursor.fetchone()

        if admin:
            session['admin']=username
            return redirect(url_for('admin_dashboard'))

        return "Invalid Admin Login"

    return render_template("admin_login.html")

@app.route('/admin_forgot_password')
def admin_forgot_password():
    return render_template("admin_forgot_password.html")

        
        


@app.route('/admin_register', methods=['GET','POST'])
def admin_register():

    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            return "Passwords not matching"

        sql = "INSERT INTO admin(username,email,password) VALUES(%s,%s,%s)"

        cursor.execute(sql,(username,email,password))

        db.commit()

        return redirect(url_for('admin_login'))

    return render_template("admin_register.html")
# ================= ADMIN DASHBOARD =================
@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    cursor.execute("SELECT * FROM applications")
    applications = cursor.fetchall()
    cursor.execute("SELECT * FROM jobs")
    jobs= cursor.fetchall()

    return render_template("admin_dashboard.html", applications=applications,jobs=jobs)


@app.route('/download_resume/<filename>')
def download_resume(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )

# ================= ADMIN ADD JOB =================
@app.route('/admin_add_job', methods=['GET','POST'])
def admin_add_job():

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':

        cursor.execute("""
        INSERT INTO jobs(title,company,location,salary,description)
        VALUES(%s,%s,%s,%s,%s)
        """,(
            request.form['title'],
            request.form['company'],
            request.form['location'],
            request.form['salary'],
            request.form['description']
        ))

        db.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_add_job.html")

# ================= UPDATE STATUS + WHATSAPP =================
@app.route('/update_status/<int:id>/<status>')
def update_status(id,status):

    cursor.execute(
        "UPDATE applications SET status=%s WHERE id=%s",
        (status,id)
    )
    db.commit()

    cursor.execute("SELECT phone_no FROM applications WHERE id=%s",(id,))
    user = cursor.fetchone()

    if user:
        try:
            client.messages.create(
                from_=TWILIO_NUMBER,
                body="Your application status updated to " + status,
                to="whatsapp:+91" + user['phone_no']
            )
        except Exception as e:
            print("Whatsapp Error:",e)

    return redirect(url_for('admin_dashboard'))

# ================= ADMIN LOGOUT =================
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin',None)
    return redirect(url_for('home'))

# ================= RUN =================
if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000,debug=True)
