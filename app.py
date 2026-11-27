import sys
import os
import re
import qrcode
from io import BytesIO
from datetime import date,datetime
from secrets import token_hex
sys.path.insert(0,'db/')
from flask import Flask,render_template,request,redirect,jsonify,abort,send_file
from dbhelper import *


app:any = Flask(__name__)


# attendance.ts is stored 24h for correct ORDER BY; render it 12h for humans
@app.template_filter('clock')
def clock(ts:str)->str:
    try:
        return datetime.strptime(ts,'%H:%M:%S').strftime('%I:%M %p').lstrip('0')
    except (ValueError,TypeError):
        return ts


@app.route("/")
def index()->None:
    return redirect('/main')


@app.route("/main")
def main()->None:
    students:list = getall('students')
    att:dict = {r['student_id']:r['status'] for r in getprocess(
        "SELECT student_id,status FROM attendance WHERE day=?",
        [date.today().isoformat()])}
    return render_template('main.html',students=students,att=att)


@app.route("/add",methods=['POST'])
def add()->None:
    addrecord('students',
        idno=request.form['idno'],
        lastname=request.form['lastname'],
        firstname=request.form['firstname'],
        course=request.form['course'],
        level=request.form['level'],
        token=token_hex(4))
    return redirect('/main')


@app.route("/delete/<int:sid>",methods=['POST'])
def delete(sid:int)->None:
    deleterecord('students',id=sid)
    return redirect('/main')


@app.route("/update/<int:sid>",methods=['POST'])
def update(sid:int)->None:
    updaterecord('students',id=sid,
        idno=request.form['idno'],
        lastname=request.form['lastname'],
        firstname=request.form['firstname'],
        course=request.form['course'],
        level=request.form['level'])
    return redirect('/main')


# PENDING means "no row for today"; ABSENT is an explicit mark that a scan can override
@app.route("/mark/<int:sid>/<status>")
def mark(sid:int,status:str)->None:
    today:str = date.today().isoformat()
    if status=='absent':
        addrecord('attendance',student_id=sid,day=today,
            ts=datetime.now().strftime('%H:%M:%S'),status='absent')
    else:
        postprocess("DELETE FROM attendance WHERE student_id=? AND day=?",[sid,today])
    return redirect('/main')


# /scan GET renders scan.html: scanner plus today's present rows
@app.route("/scan",methods=['GET','POST'])
def scan():
    if request.method=='POST':
        text:str = (request.get_json(silent=True) or {}).get('token','').strip()
        m = re.match(r'^(.*?)\s*(\d+)$', text)
        idno:str = m.group(2) if m else text
        rows:list = getrecord('students',idno=idno)
        if not rows:
            return jsonify(ok=False,status='unknown')
        student:any = rows[0]
        name:str = f"{student['lastname']}, {student['firstname']}"
        now:str = datetime.now().strftime('%H:%M:%S')
        today:str = date.today().isoformat()
        added:bool = addrecord('attendance',
            student_id=student['id'],
            day=today,
            ts=now)
        if not added:
            # row exists: flip an ABSENT mark back to PRESENT, leave a real PRESENT alone
            added = postprocess(
                "UPDATE attendance SET status='present',ts=? "
                "WHERE student_id=? AND day=? AND status<>'present'",[now,student['id'],today])
        return jsonify(ok=True,
            status='present' if added else 'already',
            name=name,
            idno=student['idno'])
    today:str = date.today().isoformat()
    rows:list = getprocess("""SELECT s.idno,s.lastname,s.firstname,a.ts
        FROM attendance a JOIN students s ON s.id=a.student_id
        WHERE a.day=? AND a.status='present' ORDER BY a.ts""",[today])
    return render_template('scan.html',rows=rows,today=today)


# kept so old /attendance links do not 404; the page now lives on /scan
@app.route("/attendance")
def attendance()->None:
    return redirect('/scan')


# QR picture built in memory from the readable payload "lastname idno": nothing is written to disk
@app.route("/qr/<int:sid>")
def qr(sid:int)->None:
    rows:list = getrecord('students',id=sid)
    if not rows: abort(404)
    payload:str = f"{(rows[0]['lastname'] or '').lower()} {rows[0]['idno']}"
    buf = BytesIO()
    qrcode.make(payload).save(buf,format='PNG')
    buf.seek(0)
    return send_file(buf,mimetype='image/png',
                     download_name=f"qr-{rows[0]['idno']}.png")


@app.route("/register")
def register()->None:
    return render_template('register.html')


# /save mirrors the professor's flow: multipart field "webcam" + form fields
@app.route("/save",methods=['POST'])
def save()->None:
    idno:str = request.form.get('idno','').strip()
    if not idno.isdigit():
        return 'IDNO must be numeric', 400
    if getrecord('students', idno=idno):
        return 'IDNO already exists', 409
    photo = request.files.get('webcam')
    if not photo:
        return 'No photo', 400
    os.makedirs(os.path.join(app.root_path,'static','img'), exist_ok=True)
    path:str = f"static/img/{idno}.png"
    photo.save(os.path.join(app.root_path,path))
    addrecord('students',
        idno=idno,
        lastname=request.form.get('lastname',''),
        firstname=request.form.get('firstname',''),
        course=request.form.get('course',''),
        level=request.form.get('level',''),
        token=token_hex(4),
        image=path)
    return '', 204


if __name__=="__main__":
    app.run(host='127.0.0.1',port=5000,debug=False)
