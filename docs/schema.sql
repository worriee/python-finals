-- db/school.db structure, dumped from the live database.
-- Documentation + rebuild reference. No app code reads this file.
-- Rebuild into an empty database:  sqlite3 db/school.db < docs/schema.sql
-- No DROP statements on purpose: this file can never wipe a live database.

CREATE TABLE students(
  id integer primary key autoincrement,
  idno varchar(10) unique,
  lastname varchar(50),
  firstname varchar(50),
  course varchar(10),
  level varchar(5),
  token varchar(16),                          -- QR payload, NULL until backfilled
  image TEXT                                  -- registration photo: static/img/<idno>.png
);

-- Unique so two students can never share a QR code.
CREATE UNIQUE INDEX idx_students_token ON students(token);

CREATE TABLE attendance(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,               -- students.id (not idno)
  day TEXT NOT NULL,                         -- ISO date: 2026-11-24
  ts TEXT NOT NULL,                          -- 24h time: 22:57:18
  status TEXT NOT NULL DEFAULT 'present',    -- present | absent; missing row = pending
  UNIQUE(student_id, day)                    -- one record per student per day
);

-- Not used by app.py. Passwords are plaintext; do not reuse this table as-is.
CREATE TABLE users(
  id integer primary key autoincrement,
  email varchar(50) unique,
  password varchar(25),
  name varchar(25)
);
