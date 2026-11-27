import sys
import os
import re
import qrcode
from io import BytesIO
from secrets import token_hex
sys.path.insert(0,'db/')
from flask import Flask,render_template,request,redirect,jsonify,abort,send_file
from dbhelper import *


app:any = Flask(__name__)


@app.route("/")
def index()->None:
    return redirect('/main')


@app.route("/main")
def main()->None:
    students:list = getall('students')
    return render_template('main.html',students=students)


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


# /scan is a viewer: it looks up the scanned student and returns their details
@app.route("/scan",methods=['GET','POST'])
def scan():
    if request.method=='POST':
        text:str = (request.get_json(silent=True) or {}).get('token','').strip()
        m = re.match(r'^(.*?)\s*(\d+)$', text)
        idno:str = m.group(2) if m else text
        rows:list = getrecord('students',idno=idno)
        if not rows:
            return jsonify(ok=False,status='unknown')
        s:any = rows[0]
        return jsonify(ok=True,
            idno=s['idno'],
            lastname=s['lastname'],
            firstname=s['firstname'],
            course=s['course'],
            level=s['level'])
    return render_template('scan.html')


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
