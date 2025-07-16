## SQL database schema
-- Main user table with all common attributes
DROP TABLE IF EXISTS users;
- CREATE TABLE users (
    - uid CHAR(8) PRIMARY KEY,
    - email VARCHAR(100) UNIQUE NOT NULL,
    - username VARCHAR(50) UNIQUE NOT NULL,
    - password VARCHAR(255) NOT NULL,
    - user_type INTEGER NOT NULL CHECK (user_type BETWEEN 1 AND 6),
    - first_name VARCHAR(50) NOT NULL,
    - last_name VARCHAR(50) NOT NULL,
    - address TEXT,
    - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    - updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    - CHECK (length(uid) = 8 AND uid GLOB '[0-9]*')
    - -- 1 = applicant, 2 = gradstudent, 3 = faculty, 4 = admin, 5 = gs, 6 = alumni
);

DROP TABLE IF EXISTS department;
- CREATE TABLE department (
    - d_num INTEGER PRIMARY KEY,
    - d_name VARCHAR(50) UNIQUE NOT NULL
);

DROP TABLE IF EXISTS faculty;
- CREATE TABLE faculty (
    - uid CHAR(8) PRIMARY KEY,
    - d_num INTEGER NOT NULL,
    - is_advisor BOOLEAN DEFAULT FALSE,
    - is_instructor BOOLEAN DEFAULT FALSE,
    - is_reviewer BOOLEAN DEFAULT FALSE,
    - is_cac BOOLEAN DEFAULT FALSE,
    - FOREIGN KEY (uid) REFERENCES users(uid),
    - FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS grad_secretary;
- CREATE TABLE grad_secretary (
    - uid CHAR(8) PRIMARY KEY,
    - FOREIGN KEY (uid) REFERENCES faculty(uid)
);

DROP TABLE IF EXISTS admin;
- CREATE TABLE admin (
    - uid CHAR(8) PRIMARY KEY,
    - FOREIGN KEY (uid) REFERENCES users(uid)
);

DROP TABLE IF EXISTS applicant;
- CREATE TABLE applicant (
    - uid CHAR(8) PRIMARY KEY,
    - semester VARCHAR(20) NOT NULL,
    - ssn CHAR(11) UNIQUE NOT NULL,
    - degree_sought VARCHAR(3) NOT NULL CHECK (degree_sought IN ('MS', 'PhD')),
    - gre_verbal INTEGER,
    - gre_quant INTEGER,
    - gre_year INTEGER,
    - work_experience TEXT,
    - areas_of_interest TEXT,
    - transcript_received BOOLEAN DEFAULT FALSE,
    - transcript_link TEXT,
    - status VARCHAR(50) DEFAULT 'incomplete',
    - payment_method TEXT DEFAULT NULL, -- 'online' or 'check'
    - payment_submitted BOOLEAN DEFAULT FALSE,
    - updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    - FOREIGN KEY (uid) REFERENCES users(uid),
    - CHECK (ssn GLOB '[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]')
);

DROP TABLE IF EXISTS gre_subject;
- CREATE TABLE gre_subject (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - applicant_uid CHAR(8) NOT NULL,
    - subject VARCHAR(50) NOT NULL,
    - score INTEGER NOT NULL,
    - year INTEGER,
    - FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS prior_degree;
- CREATE TABLE prior_degree (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - applicant_uid CHAR(8) NOT NULL,
    - degree_type VARCHAR(10) NOT NULL CHECK (degree_type IN ('Bachelors', 'Masters')),
    - year INTEGER NOT NULL,
    - gpa REAL NOT NULL,
    - university VARCHAR(100) NOT NULL,
    - FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS recommendation_letter;
- CREATE TABLE recommendation_letter (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - applicant_uid CHAR(8) NOT NULL,
    - writer_email VARCHAR(100) NOT NULL,
    - writer_title VARCHAR(100) NOT NULL,
    - institution_name VARCHAR(100) NOT NULL,
    - letter_content TEXT,
    - is_submitted BOOLEAN DEFAULT FALSE,
    - submission_date TIMESTAMP,
    - FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS recommendation_letter_review;
- CREATE TABLE recommendation_letter_review (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - letter_id INTEGER NOT NULL,
    - reviewer_id CHAR(8) NOT NULL,
    - rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    - is_generic CHAR(1) NOT NULL CHECK (is_generic IN ('Y', 'N')),
    - is_credible CHAR(1) NOT NULL CHECK (is_credible IN ('Y', 'N')),
    - FOREIGN KEY (letter_id) REFERENCES recommendation_letter(id) ON DELETE CASCADE,
    - FOREIGN KEY (reviewer_id) REFERENCES faculty(uid) ON DELETE CASCADE,
    - UNIQUE(letter_id, reviewer_id)
);

DROP TABLE IF EXISTS review;
- CREATE TABLE review (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - applicant_uid CHAR(8) NOT NULL,
    - reviewer_id CHAR(8) NOT NULL,
    - rating INTEGER NOT NULL CHECK (rating BETWEEN 0 AND 3),
    - deficiency_courses TEXT,
    - reject_reasons TEXT,
    - comment TEXT NOT NULL,
    - recommended_advisor CHAR(8),
    - decision VARCHAR(20) CHECK (decision IN ('Admit', 'Admit with Aid', 'Reject', NULL)),
    - submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    - FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE,
    - FOREIGN KEY (reviewer_id) REFERENCES faculty(uid) ON DELETE CASCADE,
    - FOREIGN KEY (recommended_advisor) REFERENCES faculty(uid)
);

DROP TABLE IF EXISTS grad_student;
- CREATE TABLE grad_student (
    - uid CHAR(8) PRIMARY KEY,
    - advisor_uid CHAR(8),
    - d_num INTEGER NOT NULL,
    - program VARCHAR(100) NOT NULL,
    - credit_hours INTEGER DEFAULT 0,
    - gpa REAL DEFAULT 0.0,
    - is_suspended BOOLEAN DEFAULT FALSE,
    - has_advising_hold BOOLEAN DEFAULT TRUE,
    - form1_submitted BOOLEAN DEFAULT FALSE,
    - form1_approved BOOLEAN DEFAULT FALSE,
    - graduation_requested BOOLEAN DEFAULT FALSE,
    - graduation_approved BOOLEAN DEFAULT FALSE,
    - thesis_submitted BOOLEAN DEFAULT FALSE,
    - thesis_approved BOOLEAN DEFAULT FALSE,
    - matriculation_date DATE,
    - FOREIGN KEY (uid) REFERENCES users(uid),
    - FOREIGN KEY (advisor_uid) REFERENCES faculty(uid),
    - FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS alumni;
- CREATE TABLE alumni (
    - uid CHAR(8) PRIMARY KEY,
    - graduation_semester VARCHAR(20) NOT NULL,
    - degree VARCHAR(50) NOT NULL,
    - FOREIGN KEY (uid) REFERENCES users(uid)
);

DROP TABLE IF EXISTS courses;
- CREATE TABLE courses (
    - crn INTEGER PRIMARY KEY,
    - course_title VARCHAR(100) NOT NULL,
    - d_num INTEGER NOT NULL,
    - credits INTEGER NOT NULL,
    - description TEXT,
    - FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS prerequisite;
- CREATE TABLE prerequisite (
    - course_id INTEGER NOT NULL,
    - prereq_id INTEGER NOT NULL,
    - PRIMARY KEY (course_id, prereq_id),
    - FOREIGN KEY (course_id) REFERENCES courses(crn),
    - FOREIGN KEY (prereq_id) REFERENCES courses(crn)
);

DROP TABLE IF EXISTS schedule;
- CREATE TABLE schedule (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - crn INTEGER NOT NULL,
    - section_num INTEGER NOT NULL,
    - semester VARCHAR(20) NOT NULL,
    - time VARCHAR(50) NOT NULL,
    - day VARCHAR(20) NOT NULL,
    - room_num VARCHAR(50) NOT NULL,
    - max_enrollment INTEGER NOT NULL,
    - current_enrollment INTEGER DEFAULT 0,
    - instructor_uid CHAR(8) NOT NULL,
    - FOREIGN KEY (crn) REFERENCES courses(crn),
    - FOREIGN KEY (instructor_uid) REFERENCES faculty(uid),
    - UNIQUE(crn, section_num, semester)
);

DROP TABLE IF EXISTS transcript;
- CREATE TABLE transcript (
    - id INTEGER PRIMARY KEY AUTOINCREMENT,
    - student_uid CHAR(8) NOT NULL,
    - crn INTEGER NOT NULL,
    - semester VARCHAR(20) NOT NULL,
    - grade VARCHAR(2),
    - grade_edited BOOLEAN DEFAULT FALSE,
    - FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    - FOREIGN KEY (crn) REFERENCES courses(crn),
    - UNIQUE(student_uid, crn, semester)
);

DROP TABLE IF EXISTS form_courses;
- CREATE TABLE form_courses (
    - student_uid CHAR(8) NOT NULL,
    - crn INTEGER NOT NULL,
    - semester_planned VARCHAR(20),
    - PRIMARY KEY (student_uid, crn),
    - FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    - FOREIGN KEY (crn) REFERENCES courses(crn)
);

DROP TABLE IF EXISTS thesis;
- CREATE TABLE thesis (
    - student_uid CHAR(8) PRIMARY KEY,
    - title TEXT NOT NULL,
    - abstract TEXT NOT NULL,
    - submission_date DATE,
    - approval_date DATE,
    - advisor_uid CHAR(8) NOT NULL,
    - FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    - FOREIGN KEY (advisor_uid) REFERENCES faculty(uid)
);

DROP TABLE IF EXISTS enrollment;
- CREATE TABLE enrollment (
    - student_uid CHAR(8),
    - schedule_id INTEGER,
    - enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    - PRIMARY KEY (student_uid, schedule_id),
    - FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    - FOREIGN KEY (schedule_id) REFERENCES schedule(id)
);

CREATE TRIGGER update_user_timestamp AFTER UPDATE ON users
- BEGIN
    - UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
- END;

CREATE TRIGGER update_applicant_timestamp AFTER UPDATE ON applicant
- BEGIN
    - UPDATE applicant SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
    - UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
- END;

CREATE TRIGGER update_grad_student_timestamp AFTER UPDATE ON grad_student
- BEGIN
    - UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
- END;

CREATE INDEX idx_grad_student_advisor ON grad_student(advisor_uid);

CREATE INDEX idx_transcript_student ON transcript(student_uid);

INSERT INTO department (d_num, d_name) VALUES 
- (1, 'CSCI'),
- (2, 'ECE'),
- (3, 'MATH');

INSERT INTO courses (crn, course_title, d_num, credits) VALUES
- (6221, 'SW Paradigms', 1, 3),
- (6461, 'Computer Architecture', 1, 3),
- (6212, 'Algorithms', 1, 3),
- (6220, 'Machine Learning', 1, 3),
- (6232, 'Networks 1', 1, 3),
- (6233, 'Networks 2', 1, 3),
- (6241, 'Database 1', 1, 3),
- (6242, 'Database 2', 1, 3),
- (6246, 'Compilers', 1, 3),
- (6260, 'Multimedia', 1, 3),
- (6251, 'Cloud Computing', 1, 3),
- (6254, 'SW Engineering', 1, 3),
- (6262, 'Graphics 1', 1, 3),
- (6283, 'Security 1', 1, 3),
- (6284, 'Cryptography', 1, 3),
- (6286, 'Network Security', 1, 3),
- (6325, 'Algorithms 2', 1, 3),
- (6339, 'Embedded Systems', 1, 3),
- (6384, 'Cryptography 2', 1, 3),
- (6243, 'Communication Theory', 2, 3),
- (6244, 'Information Theory', 2, 2),
- (6210, 'Logic', 3, 2);

INSERT INTO prerequisite (course_id, prereq_id) VALUES
- (6233, 6232),
- (6242, 6241),
- (6246, 6461),
- (6246, 6212),
- (6251, 6461),
- (6254, 6221),
- (6283, 6212),
- (6286, 6283),
- (6286, 6232),
- (6325, 6212),
- (6339, 6461),
- (6339, 6212),
- (6384, 6284);

-- SCHEDULE SCHEMAA
INSERT INTO schedule (crn, section_num, semester, time, day, room_num, max_enrollment, instructor_uid) VALUES
- (6221, 1, 'Spring 25', '1500—1730', 'M', 'SEH 1300', 50, '11111111'),
- (6220, 1, 'Spring 25', '1600—1830', 'W', 'SEH 1300', 50, '33333333'),
- (6461, 1, 'Spring 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
- (6212, 1, 'Spring 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
- (6232, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '11111111'),
- (6233, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '22222222'),
- (6241, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6242, 1, 'Spring 25', '1800—2030', 'R', 'SEH 1300', 50, '11111111'),
- (6246, 1, 'Spring 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
- (6251, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '33333333'),
- (6254, 1, 'Spring 25', '1530—1800', 'M', 'SEH 1300', 50, '11111111'),
- (6260, 1, 'Spring 25', '1800—2030', 'R', 'SEH 1300', 50, '22222222'),
- (6262, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6283, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '11111111'),
- (6284, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
- (6286, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6384, 1, 'Spring 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
- (6243, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
- (6244, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '33333333'),
- (6210, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '11111111'),
- (6339, 1, 'Spring 25', '1600—1830', 'R', 'SEH 1300', 50, '22222222'),
- (6325, 1, 'Spring 25', '1600—1830', 'R', 'SEH 1300', 50, '33333333'),
- (6325, 1, 'Fall 25', '1600—1830', 'R', 'SEH 1300', 50, '33333333'),
- (6221, 1, 'Fall 25', '1500—1730', 'M', 'SEH 1300', 50, '11111111'),
- (6220, 1, 'Fall 25', '1600—1830', 'W', 'SEH 1300', 50, '33333333'),
- (6461, 1, 'Fall 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
- (6212, 1, 'Fall 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
- (6232, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '11111111'),
- (6233, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '22222222'),
- (6241, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6242, 1, 'Fall 25', '1800—2030', 'R', 'SEH 1300', 50, '11111111'),
- (6246, 1, 'Fall 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
- (6251, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '33333333'),
- (6254, 1, 'Fall 25', '1530—1800', 'M', 'SEH 1300', 50, '11111111'),
- (6260, 1, 'Fall 25', '1800—2030', 'R', 'SEH 1300', 50, '22222222'),
- (6262, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6283, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '11111111'),
- (6284, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
- (6286, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
- (6384, 1, 'Fall 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
- (6243, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
- (6244, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '33333333'),
- (6210, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '11111111'),
- (6339, 1, 'Fall 25', '1600—1830', 'R', 'SEH 1300', 50, '22222222');
