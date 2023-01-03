from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_mail import Mail, Message
from flask_session import Session

from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__, template_folder='templates')

#configure session
app.config['SECRET_KEY'] = '3032FC23ECworkly'
app.config["SESSION_TYPE"] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

app.config.update(dict(
    MAIL_SERVER = 'smtp-mail.outlook.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS = True,
    MAIL_USE_SSL = False,
    MAIL_SUPPRESS_SEND = False,
    MAIL_USERNAME = 'jelmourne@outlook.com',
    MAIL_PASSWORD = 'Bruce-12'
))
mail = Mail(app)

#configure data base
db = sqlite3.connect('workly.db', check_same_thread=False)
cursor = db.cursor()

#functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def format(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "{hour}:{min}:{sec}".format(hour=int(h), min=int(m), sec=int(s)) 

#homepage
@app.route("/")
@login_required
def index():
    return render_template('homepage.html', admin=session.get("admin"))      
    
#login user
@app.route("/login", methods=["GET","POST"])
def login():

    if session.get("user_id") is None:

        if request.method == "POST": 

            #check for blank email
            if not request.form.get("email"):
                flash('Input a email', category='danger') 
                return redirect("/login")

            #check for blank password
            elif not request.form.get("password"):
                flash('Input a password', category='danger')
                return redirect("/login")

            #check if user exists 
            data = cursor.execute("SELECT * FROM users WHERE email = ?", 
            [request.form.get("email")]).fetchall()

            #login user
            if len(data) != 1 or not check_password_hash(data[0][3], request.form.get("password")):
                flash('Invalid credentials', category='danger')
                return redirect("/login")

            else:
                if request.form.get("remember") is not None:
                    session.permanent = True
                
                session["admin"] = (data[0][4])
                session["user_id"] = (data[0][0])           
                flash('Sucessfully logged in', category='success')
                return redirect("/")
            
        elif request.method == "GET": 
            return render_template("login.html")

    else:
        session.clear()
        return redirect("/login")
    
#register user
@app.route("/register", methods=["GET", "POST"])
def register():

    if session.get("user_id") is None:

        if request.method == "POST":
    
            #check for blank firstname
            if not request.form.get("firstname"):
                flash('Input a firstname', category='danger')
                return redirect("/register")
            
            #check for blank lastname
            elif not request.form.get("lastname"):
                flash('Input a lastname', category='danger')
                return redirect("/register")

            #check for blank email
            elif not request.form.get("email"):
                flash('Input a email', category='danger')
                return redirect("/register")
        
            #check for blank password
            elif not request.form.get("password"):
                flash('Input a password', category='danger')
                return redirect("/register")

            #check if user exists
            data = cursor.execute("SELECT * FROM users WHERE email=?", [request.form.get('email')]).fetchall()
            
            if len(data) != 1:    
                #register user
                cursor.execute("INSERT INTO users (name, email, hash, employ) VALUES (?,?,?,?)",
                ((''.join(filter(str.isalpha, (request.form.get('firstname').lower()).capitalize()))+" "+
                ''.join(filter(str.isalpha, (request.form.get('lastname').lower()).capitalize()))), 
                request.form.get('email'), generate_password_hash(request.form.get('password')), request.form.get('employ')))
                db.commit()

                user_data = cursor.execute("SELECT * FROM users WHERE email=?", [request.form.get('email')]).fetchall()

                session["user_id"] = (user_data[0][0])
                flash('Sucessfully registered', category='success')
                return redirect("/")
            
            else:
                flash('User already exists', category='danger')
                return redirect("/register")

        elif request.method == "GET": 
            employer = cursor.execute("SELECT id, name FROM users WHERE admin >='1'").fetchall()
            return render_template("register.html", employer=employer)
    else:
        session.clear()
        return redirect("/register")

#logout user
@app.route("/logout")
@login_required
def logout():

    session.clear()
    flash('Succesfully logged out', category='success')
    return redirect("/login")

#start
@app.route("/start", methods=["GET", "POST"])
@login_required
def start():

    if request.method == "POST":
        
        data = cursor.execute("SELECT * FROM hours WHERE user_id=? and end IS NULL", str(session.get("user_id"))).fetchall()

        if len(data) != 0:
            flash('Already started', category='danger')
            return redirect("/")

        elif not request.form.get("location"):
            flash('Invalid location', category='danger')
            return redirect("/start")

        else:
            user_data = cursor.execute("SELECT id,name FROM users WHERE id=?", str(session.get("user_id"))).fetchall()

            cursor.execute("INSERT INTO hours (user_id,name,location,date,start) VALUES (?,?,?,?,?)",
            (user_data[0][0],user_data[0][1],str(request.form.get("location"))[:15],request.form.get("date"),request.form.get("time")))
            db.commit()

            flash('Successfully started shift', category='success')
            return redirect("/")
        
    elif request.method == "GET":
        locations = cursor.execute("SELECT * FROM locations").fetchall()

        return render_template("start.html", locations=locations, admin=session.get("admin"))

#end
@app.route("/end", methods=["GET", "POST"])
@login_required
def end():

    if request.method == "POST":

        print(request.form.get("description"))

        data = cursor.execute("SELECT * FROM hours WHERE user_id=? and end IS NULL",str(session.get("user_id"))).fetchall()

        if len(data) != 1:
            flash('Have not started', category='danger')
            return redirect("/")
        
        elif not request.form.get("description"):
            flash('Invalid description', category='danger')
            return redirect("/end")
        
        else:
            hours = (datetime.strptime(request.form.get("time"),'%H:%M') - datetime.strptime(data[0][6], '%H:%M')).total_seconds()
            
            if hours == timedelta(seconds=0):
                flash('Have not worked long enough', category='danger')
                return redirect("/")

            if data[0][9] is not None:
                adjhours = (datetime.strptime(str(format(hours)), '%H:%M:%S') - timedelta(minutes=int(data[0][9])))

                if hours < timedelta(minutes=int(data[0][9])).total_seconds():
                    cursor.execute("UPDATE hours SET description=?, end=?, hours=? WHERE user_id=? and end IS NULL",
                    (str(request.form.get("description"))[:15], request.form.get("time"), "0h0", str(session.get("user_id"))))
                    db.commit()

                    flash('Successfully ended shift', category='success')
                    return redirect("/")

                else:
                    cursor.execute("UPDATE hours SET description=?, hours=? WHERE user_id=? and end IS NULL",
                    (str(request.form.get("description"))[:15], request.form.get("time"), 'h'.join(str(adjhours).split(':')[:2]), str(session.get("user_id"))))
                    db.commit()

                    flash('Successfully ended shift', category='success')
                    return redirect("/")
            else:
                cursor.execute("UPDATE hours SET description=?, end=?, hours=? WHERE user_id=? and end IS NULL",
                (str(request.form.get("description"))[:15], request.form.get("time"), 'h'.join(str(format(hours)).split(':')[:2]), str(session.get("user_id"))))
                db.commit()
                
                flash('Successfully ended shift', category='success')
                return redirect("/")
            
    elif request.method == "GET":
        return render_template("end.html", admin=session.get("admin"))

#break
@app.route("/break", methods=["GET", "POST"])
@login_required
def breaks():

    if request.method == "POST":
        data = cursor.execute("SELECT * FROM hours WHERE user_id=? and end IS NULL",str(session.get("user_id"))).fetchall()

        if len(data) != 1:
            flash('Have not started', category='danger')
            return redirect("/")

        else:
            #add to current time if already clocked in
            if data[0][9] is None:
                cursor.execute("UPDATE hours SET break=? WHERE user_id=? and end IS NULL",
                (request.form.get("break"), str(session.get("user_id"))))
                db.commit()

                flash('Successfully took break', category='success')
                return redirect("/")
            else:
                adjbreak = int(data[0][9]) + int(request.form.get("break"))

                cursor.execute("UPDATE hours SET break=? WHERE user_id=? and end IS NULL",
                (adjbreak, str(session.get("user_id"))))
                db.commit()
                
                flash('Successfully took break', category='success')
                return redirect("/")
                
    elif request.method == "GET":
        return render_template("break.html", admin=session.get("admin"))

#details
@app.route("/details", methods=["GET"])
@login_required
def details():
    
    #check if admin
    print(session.get("admin"))
    if session.get("admin") is None:
        hours = cursor.execute("SELECT * FROM hours WHERE user_id=?", str(session.get("user_id"))).fetchall()
        return render_template("detail.html", hours=hours)
    
    elif session.get("admin") == 0:
        hours = cursor.execute("SELECT * FROM hours").fetchall()
        return render_template("detailadmin.html", hours=hours)
    
    elif session.get("admin") > 0:
        hours = cursor.execute("SELECT * FROM hours INNER JOIN users ON users.id=hours.user_id WHERE users.employ=? or users.id=?", 
        [session.get("admin"),session.get("user_id")]).fetchall()
        return render_template("detailadmin.html", hours=hours)

#settings
@app.route("/settings", methods=["GET"])
@login_required
def settings():
    return render_template("setting.html", admin=session.get("admin"))

#admin control
@app.route("/admin", methods= ["GET", "POST"])
@login_required
def admin():

    if request.method == "POST":
        
        if not request.form.get('location'):
            flash('Invalid location', category='danger')
            return redirect("/admin")
        
        cursor.execute("INSERT INTO locations (location) VALUES (?)", 
        [request.form.get('location')])
        db.commit()

        return redirect("/admin")

    elif request.method == "GET":
        if session.get("admin") is not None:
            locations = cursor.execute("SELECT * FROM locations")
            return render_template("admin.html", locations=locations)

        else: 
            flash("Don't have permission", category='danger')
            return redirect("/")

#delete row
@app.route("/delete", methods=["POST"])
@login_required
def delete():
   
    cursor.execute("DELETE FROM {} WHERE id=?"
    .format(request.form.get("table")), [request.form.get("id")])
    db.commit()
    
    return redirect(request.referrer)

#delete table
@app.route("/delete/table", methods=["POST"])
@login_required
def deletetable():
    
    cursor.execute("DELETE FROM hours")
    db.commit()
    
    return redirect(request.referrer)

#delete account
@app.route("/delete/account", methods=["POST"])
@login_required
def deleteaccount():

    cursor.execute("DELETE FROM users WHERE id=?", str(session.get("user_id")))
    cursor.execute("DELETE FROM hours WHERE user_id=?", str(session.get("user_id")))
    db.commit()

    session.clear()
    flash('Successfully deleted account', category='success')
    return redirect("/login")

#reset page
@app.route("/reset", methods=["GET"])
def reset():
    if request.method == "GET":
        return render_template("reset.html")

#reset password
@app.route("/reset/password", methods=["GET","POST"])
def resetpass():
    if request.method == "POST":

        #check for blank email
        if not request.form.get("email"):
            flash('Input a email', category='danger')
            return redirect("/reset/password")
    
        #check for blank password
        elif not request.form.get("password"):
            flash('Input a password', category='danger')
            return redirect("/reset/password")

        data = cursor.execute("SELECT * FROM users WHERE email = ?", 
            [request.form.get("email")]).fetchall()

        if len(data) != 1:
            flash('Invalid credentials', category='danger')
            return redirect("/reset/password")
        
        cursor.execute("UPDATE users SET hash=? WHERE email=?", 
        (generate_password_hash(request.form.get('password')), request.form.get('email')))
        db.commit()

        session.clear()
        flash('Succesfully changed password', category='success')
        return redirect("/login")

    elif request.method == "GET":
        return render_template("resetpass.html", admin = session.get("admin"), logged = session.get("user_id"))

#reset email
@app.route("/reset/email", methods=["GET","POST"])
def resetemail():
    if request.method == "POST":

        #check for blank email
        if not request.form.get("email"):
            flash('Input a email', category='danger')
            return redirect("/reset/email")
    
        #check for blank password
        elif not request.form.get("password"):
            flash('Input a password', category='danger')
            return redirect("/reset/email")

        data = cursor.execute("SELECT * FROM users WHERE email = ?", 
            [request.form.get("email")]).fetchall()
     
        if len(data) != 1 or not check_password_hash(data[0][3], request.form.get("password")):
            flash('Invalid credentials', category='danger')
            return redirect("/reset/email")

        cursor.execute("UPDATE users SET email=? WHERE id=?", 
        ((request.form.get('email')), data[0][0]))
        db.commit()

        session.clear()
        flash('Succesfully changed email', category='success')
        return redirect("/login")

    elif request.method == "GET":
        return render_template("resetemail.html", admin = session.get("admin"), logged = session.get("user_id"))

#change employer
@app.route("/change/employer", methods=["GET", "POST"])
def changeemployer():
    
    if request.method == "POST":
        
        if not request.form.get("employ"):
            flash('Invalid employer', category='danger')
            return redirect("/change/employer")
        
        cursor.execute("UPDATE users SET employ=? WHERE id=?", 
        (request.form.get("employ"), session.get("user_id")))
        db.commit()
        
        flash('Successfully changed employer', category='success')
        return redirect("/")
    
    elif request.method == "GET":
        employer = cursor.execute("SELECT id, name FROM users WHERE admin >='1'").fetchall()
        return render_template("employer.html",  admin=session.get("admin"), employer=employer)

#report bug
@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":

        msg = Message('Bug report', sender = 'jelmourne@outlook.com', recipients = ['jelmourne@outlook.com'])
        msg.body = request.form.get("description")
        mail.send(msg)

        flash('Successfully sent message', category='success')
        return redirect("/settings")

    elif request.method == "GET":
        return render_template("report.html", admin=session.get("admin"))
    
if __name__ == "__main__":
    app.run()