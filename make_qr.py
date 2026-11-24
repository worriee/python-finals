from os import makedirs
from sqlite3 import connect
import qrcode

makedirs('qr', exist_ok=True)
conn = connect('db/school.db')
conn.execute('UPDATE students SET token=lower(hex(randomblob(4))) WHERE token IS NULL')
conn.commit()
rows = conn.execute('SELECT idno,token FROM students').fetchall()
conn.close()
for idno, token in rows:
    qrcode.make(token).save(f'qr/{idno}.png')
print(f"{len(rows)} QR codes written to qr/")
