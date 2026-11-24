import sys
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
    att:dict = {r['student_id']:r['ts'] for r in getprocess(
        "SELECT student_id,ts FROM attendance WHERE day=?",
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
        lastname=request.form['lastname'],
        firstname=request.form['firstname'],
        course=request.form['course'],
        level=request.form['level'])
    return redirect('/main')


# /scan GET renders base.html directly: its default content block holds the scanner and today's rows
@app.route("/scan",methods=['GET','POST'])
def scan():
    if request.method=='POST':
        token:str = (request.get_json(silent=True) or {}).get('token','')
        rows:list = getrecord('students',token=token)
        if not rows:
            return jsonify(ok=False,status='unknown')
        student:any = rows[0]
        name:str = f"{student['lastname']}, {student['firstname']}"
        added:bool = addrecord('attendance',
            student_id=student['id'],
            day=date.today().isoformat(),
            ts=datetime.now().strftime('%H:%M:%S'))
        return jsonify(ok=True,
            status='present' if added else 'already',
            name=name,
            idno=student['idno'])
    today:str = date.today().isoformat()
    rows:list = getprocess("""SELECT s.idno,s.lastname,s.firstname,a.ts
        FROM attendance a JOIN students s ON s.id=a.student_id
        WHERE a.day=? ORDER BY a.ts""",[today])
    return render_template('base.html',rows=rows,today=today)


# kept so old /attendance links do not 404; the page now lives on /scan
@app.route("/attendance")
def attendance()->None:
    return redirect('/scan')


# QR picture built in memory from students.token: nothing is written to disk
@app.route("/qr/<int:sid>")
def qr(sid:int)->None:
    rows:list = getrecord('students',id=sid)
    if not rows: abort(404)
    token:str = rows[0]['token']
    if not token:
        token = token_hex(4)
        updaterecord('students',id=sid,token=token)
    buf = BytesIO()
    qrcode.make(token).save(buf,format='PNG')
    buf.seek(0)
    return send_file(buf,mimetype='image/png',
                     download_name=f"qr-{rows[0]['idno']}.png")


if __name__=="__main__":
    app.run(host='127.0.0.1',port=5000,debug=False)
