from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from dotenv import load_dotenv
import os

# ---------------- Setup ----------------
app = Flask(__name__)
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", "Root@123"),
    "database": os.getenv("DB_NAME", "sports_equipment_db")
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ---------------- Routes ----------------

@app.route('/')
def index():
    return render_template('index.html')


# --- Add Student ---
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        class_name = request.form['class']
        phone = request.form['phone']
        cur.execute("INSERT INTO students (name, roll_no, class, phone) VALUES (%s,%s,%s,%s)",
                    (name, roll_no, class_name, phone))
        conn.commit()

    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_student.html', students=students)


# --- Add Equipment ---
@app.route('/add_equipment', methods=['GET', 'POST'])
def add_equipment():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        cur.execute("INSERT INTO equipments (name, quantity) VALUES (%s,%s)", (name, quantity))
        conn.commit()

    cur.execute("SELECT * FROM equipments")
    equipments = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_equipment.html', equipments=equipments)


# --- View Students ---
@app.route('/students')
def students():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('students.html', students=data)


# --- View Equipments ---
@app.route('/equipments')
def equipments():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM equipments")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('equipments.html', equipments=data)


# --- Issue Equipment ---
@app.route('/issue', methods=['GET', 'POST'])
def issue_equipment():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    cur.execute("SELECT * FROM equipments")
    equipments = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form['student_id']
        equipment_id = request.form['equipment_id']
        issue_time = datetime.now()
        due_time = issue_time + timedelta(minutes=1)   # For demo (1 min); change to hours=8 for real use

        cur.execute("""
            INSERT INTO issues (student_id, equipment_id, issue_time, due_time, status)
            VALUES (%s, %s, %s, %s, 'issued')
        """, (student_id, equipment_id, issue_time, due_time))
        cur.execute("UPDATE equipments SET quantity = quantity - 1 WHERE equipment_id = %s", (equipment_id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('view_issues'))

    cur.close()
    conn.close()
    return render_template('issue_equipment.html', students=students, equipments=equipments)


# --- Return Equipment ---
@app.route('/return/<int:issue_id>')
def return_equipment(issue_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE issues SET status='returned', return_time=%s WHERE issue_id=%s", (datetime.now(), issue_id))
    cur.execute("""
        UPDATE equipments 
        SET quantity = quantity + 1
        WHERE equipment_id = (SELECT equipment_id FROM issues WHERE issue_id = %s)
    """, (issue_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('view_issues'))


# --- View Issues ---
@app.route('/issues')
def view_issues():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT i.*, s.name AS student_name, e.name AS equipment_name
        FROM issues i
        JOIN students s ON i.student_id = s.student_id
        JOIN equipments e ON i.equipment_id = e.equipment_id
        ORDER BY i.issue_time DESC
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('issues.html', issues=data)


# ---------------- Reminder Checker ----------------

def check_overdue_and_send_sms():
    print("🔍 Checking for overdue equipment...")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    now = datetime.now()

    cur.execute("""
        SELECT i.issue_id, s.name AS student_name, s.phone, e.name AS equipment_name, 
               i.issue_time, i.due_time
        FROM issues i
        JOIN students s ON i.student_id = s.student_id
        JOIN equipments e ON i.equipment_id = e.equipment_id
        WHERE i.status = 'issued' AND i.due_time < %s 
              AND (i.reminder_sent = 0 OR i.reminder_sent IS NULL)
    """, (now,))

    overdue = cur.fetchall()
    if not overdue:
        print("✅ No overdue issues.")
        cur.close()
        conn.close()
        return

    for record in overdue:
        student_name = record["student_name"]
        phone = record["phone"]
        equipment = record["equipment_name"]
        issue_time = record["issue_time"]

        message = (
            f"Reminder: Dear {student_name}, please return the {equipment} "
            f"you borrowed at {issue_time.strftime('%H:%M %d-%m-%Y')} to the sports department."
        )

        # Simulated SMS print
        print("------------------------------------------------------------")
        print(f"📩 [SIMULATED SMS] To: {phone}")
        print(f"Message: {message}")
        print("------------------------------------------------------------")

        cur.execute("UPDATE issues SET reminder_sent = 1 WHERE issue_id = %s", (record["issue_id"],))
        conn.commit()

    cur.close()
    conn.close()
    print("✅ Reminder check complete.\n")


scheduler = BackgroundScheduler()
scheduler.add_job(func=check_overdue_and_send_sms, trigger="interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# --- Delete Student ---
@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM issues WHERE student_id = %s", (student_id,))
    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        return "⚠️ Cannot delete student with existing issue records."

    cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('add_student'))


# --- Delete Equipment ---
@app.route('/delete_equipment/<int:equipment_id>')
def delete_equipment(equipment_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM issues WHERE equipment_id = %s AND status='issued'", (equipment_id,))
    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        return "⚠️ Cannot delete equipment that is currently issued."

    cur.execute("DELETE FROM equipments WHERE equipment_id = %s", (equipment_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('add_equipment'))


# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)
