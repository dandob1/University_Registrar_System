-- Main user table with all common attributes
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    uid CHAR(8) PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    user_type INTEGER NOT NULL CHECK (user_type BETWEEN 1 AND 6),
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(uid) = 8 AND uid GLOB '[0-9]*')
    -- 1 = applicant, 2 = gradstudent, 3 = faculty, 4 = admin, 5 = gs, 6 = alumni
);

DROP TABLE IF EXISTS department;
CREATE TABLE department (
    d_num INTEGER PRIMARY KEY,
    d_name VARCHAR(50) UNIQUE NOT NULL
);

DROP TABLE IF EXISTS faculty;
CREATE TABLE faculty (
    uid CHAR(8) PRIMARY KEY,
    d_num INTEGER NOT NULL,
    is_advisor BOOLEAN DEFAULT FALSE,
    is_instructor BOOLEAN DEFAULT FALSE,
    is_reviewer BOOLEAN DEFAULT FALSE,
    is_cac BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS grad_secretary;
CREATE TABLE grad_secretary (
    uid CHAR(8) PRIMARY KEY,
    FOREIGN KEY (uid) REFERENCES faculty(uid)
);

DROP TABLE IF EXISTS admin;
CREATE TABLE admin (
    uid CHAR(8) PRIMARY KEY,
    FOREIGN KEY (uid) REFERENCES users(uid)
);

DROP TABLE IF EXISTS applicant;
CREATE TABLE applicant (
    uid CHAR(8) PRIMARY KEY,
    semester VARCHAR(20) NOT NULL,
    ssn CHAR(11) UNIQUE NOT NULL,
    degree_sought VARCHAR(3) NOT NULL CHECK (degree_sought IN ('MS', 'PhD')),
    gre_verbal INTEGER,
    gre_quant INTEGER,
    gre_year INTEGER,
    work_experience TEXT,
    areas_of_interest TEXT,
    transcript_received BOOLEAN DEFAULT FALSE,
    transcript_link TEXT,
    status VARCHAR(50) DEFAULT 'incomplete',
    payment_method TEXT DEFAULT NULL, -- 'online' or 'check'
    payment_submitted BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uid) REFERENCES users(uid),
    CHECK (ssn GLOB '[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]')
);

DROP TABLE IF EXISTS gre_subject;
CREATE TABLE gre_subject (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_uid CHAR(8) NOT NULL,
    subject VARCHAR(50) NOT NULL,
    score INTEGER NOT NULL,
    year INTEGER,
    FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS prior_degree;
CREATE TABLE prior_degree (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_uid CHAR(8) NOT NULL,
    degree_type VARCHAR(10) NOT NULL CHECK (degree_type IN ('Bachelors', 'Masters')),
    year INTEGER NOT NULL,
    gpa REAL NOT NULL,
    university VARCHAR(100) NOT NULL,
    FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS recommendation_letter;
CREATE TABLE recommendation_letter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_uid CHAR(8) NOT NULL,
    writer_name VARCHAR(100) NOT NULL,
    writer_email VARCHAR(100) NOT NULL,
    writer_title VARCHAR(100) NOT NULL,
    institution_name VARCHAR(100) NOT NULL,
    letter_content TEXT,
    is_submitted BOOLEAN DEFAULT FALSE,
    submission_date TIMESTAMP,
    FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE
);

DROP TABLE IF EXISTS recommendation_letter_review;
CREATE TABLE recommendation_letter_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_id INTEGER NOT NULL,
    reviewer_id CHAR(8) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    is_generic CHAR(1) NOT NULL CHECK (is_generic IN ('Y', 'N')),
    is_credible CHAR(1) NOT NULL CHECK (is_credible IN ('Y', 'N')),
    FOREIGN KEY (letter_id) REFERENCES recommendation_letter(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES faculty(uid) ON DELETE CASCADE,
    UNIQUE(letter_id, reviewer_id)
);

DROP TABLE IF EXISTS review;
CREATE TABLE review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_uid CHAR(8) NOT NULL,
    reviewer_id CHAR(8) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 0 AND 3),
    deficiency_courses TEXT,
    reject_reasons TEXT,
    comment TEXT NOT NULL,
    recommended_advisor CHAR(8),
    decision VARCHAR(20) CHECK (decision IN ('Admit', 'Admit with Aid', 'Reject', NULL)),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (applicant_uid) REFERENCES applicant(uid) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES faculty(uid) ON DELETE CASCADE,
    FOREIGN KEY (recommended_advisor) REFERENCES faculty(uid)
);

DROP TABLE IF EXISTS grad_student;
CREATE TABLE grad_student (
    uid CHAR(8) PRIMARY KEY,
    advisor_uid CHAR(8),
    d_num INTEGER NOT NULL,
    program VARCHAR(100) NOT NULL,
    credit_hours INTEGER DEFAULT 0,
    gpa REAL DEFAULT 0.0,
    is_suspended BOOLEAN DEFAULT FALSE,
    has_advising_hold BOOLEAN DEFAULT TRUE,
    form1_submitted BOOLEAN DEFAULT FALSE,
    form1_approved BOOLEAN DEFAULT FALSE,
    graduation_requested BOOLEAN DEFAULT FALSE,
    graduation_approved BOOLEAN DEFAULT FALSE,
    thesis_submitted BOOLEAN DEFAULT FALSE,
    thesis_approved BOOLEAN DEFAULT FALSE,
    matriculation_date DATE,
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (advisor_uid) REFERENCES faculty(uid),
    FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS alumni;
CREATE TABLE alumni (
    uid CHAR(8) PRIMARY KEY,
    graduation_semester VARCHAR(20) NOT NULL,
    degree VARCHAR(50) NOT NULL,
    FOREIGN KEY (uid) REFERENCES users(uid)
);

DROP TABLE IF EXISTS courses;
CREATE TABLE courses (
    crn INTEGER PRIMARY KEY,
    course_title VARCHAR(100) NOT NULL,
    d_num INTEGER NOT NULL,
    credits INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY (d_num) REFERENCES department(d_num)
);

DROP TABLE IF EXISTS prerequisite;
CREATE TABLE prerequisite (
    course_id INTEGER NOT NULL,
    prereq_id INTEGER NOT NULL,
    PRIMARY KEY (course_id, prereq_id),
    FOREIGN KEY (course_id) REFERENCES courses(crn),
    FOREIGN KEY (prereq_id) REFERENCES courses(crn)
);

DROP TABLE IF EXISTS schedule;
CREATE TABLE schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crn INTEGER NOT NULL,
    section_num INTEGER NOT NULL,
    semester VARCHAR(20) NOT NULL,
    time VARCHAR(50) NOT NULL,
    day VARCHAR(20) NOT NULL,
    room_num VARCHAR(50) NOT NULL,
    max_enrollment INTEGER NOT NULL,
    current_enrollment INTEGER DEFAULT 0,
    instructor_uid CHAR(8) NOT NULL,
    FOREIGN KEY (crn) REFERENCES courses(crn),
    FOREIGN KEY (instructor_uid) REFERENCES faculty(uid),
    UNIQUE(crn, section_num, semester)
);

DROP TABLE IF EXISTS transcript;
CREATE TABLE transcript (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_uid CHAR(8) NOT NULL,
    crn INTEGER NOT NULL,
    semester VARCHAR(20) NOT NULL,
    grade VARCHAR(2),
    grade_edited BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    FOREIGN KEY (crn) REFERENCES courses(crn),
    UNIQUE(student_uid, crn, semester)
);

DROP TABLE IF EXISTS form_courses;
CREATE TABLE form_courses (
    student_uid CHAR(8) NOT NULL,
    crn INTEGER NOT NULL,
    semester_planned VARCHAR(20),
    PRIMARY KEY (student_uid, crn),
    FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    FOREIGN KEY (crn) REFERENCES courses(crn)
);

DROP TABLE IF EXISTS thesis;
CREATE TABLE thesis (
    student_uid CHAR(8) PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    submission_date DATE,
    approval_date DATE,
    advisor_uid CHAR(8) NOT NULL,
    FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    FOREIGN KEY (advisor_uid) REFERENCES faculty(uid)
);
-- WILL THIS BE USEFUL??????????
DROP TABLE IF EXISTS enrollment;
CREATE TABLE enrollment (
    student_uid CHAR(8),
    schedule_id INTEGER,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_uid, schedule_id),
    FOREIGN KEY (student_uid) REFERENCES grad_student(uid),
    FOREIGN KEY (schedule_id) REFERENCES schedule(id)
);

CREATE TRIGGER update_user_timestamp AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
END;

CREATE TRIGGER update_applicant_timestamp AFTER UPDATE ON applicant
BEGIN
    UPDATE applicant SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
END;

CREATE TRIGGER update_grad_student_timestamp AFTER UPDATE ON grad_student
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE uid = NEW.uid;
END;

CREATE INDEX idx_grad_student_advisor ON grad_student(advisor_uid);
CREATE INDEX idx_transcript_student ON transcript(student_uid);

INSERT INTO department (d_num, d_name) VALUES 
(1, 'CSCI'),
(2, 'ECE'),
(3, 'MATH');

INSERT INTO courses (crn, course_title, d_num, credits) VALUES
(6221, 'SW Paradigms', 1, 3),
(6461, 'Computer Architecture', 1, 3),
(6212, 'Algorithms', 1, 3),
(6220, 'Machine Learning', 1, 3),
(6232, 'Networks 1', 1, 3),
(6233, 'Networks 2', 1, 3),
(6241, 'Database 1', 1, 3),
(6242, 'Database 2', 1, 3),
(6246, 'Compilers', 1, 3),
(6260, 'Multimedia', 1, 3),
(6251, 'Cloud Computing', 1, 3),
(6254, 'SW Engineering', 1, 3),
(6262, 'Graphics 1', 1, 3),
(6283, 'Security 1', 1, 3),
(6284, 'Cryptography', 1, 3),
(6286, 'Network Security', 1, 3),
(6325, 'Algorithms 2', 1, 3),
(6339, 'Embedded Systems', 1, 3),
(6384, 'Cryptography 2', 1, 3),
(6243, 'Communication Theory', 2, 3),
(6244, 'Information Theory', 2, 2),
(6210, 'Logic', 3, 2);

INSERT INTO prerequisite (course_id, prereq_id) VALUES
(6233, 6232),
(6242, 6241),
(6246, 6461),
(6246, 6212),
(6251, 6461),
(6254, 6221),
(6283, 6212),
(6286, 6283),
(6286, 6232),
(6325, 6212),
(6339, 6461),
(6339, 6212),
(6384, 6284);


INSERT INTO users (uid, email, username, password, user_type, first_name, last_name, address) VALUES
('34567890', 'bob.johnson@example.com', 'bjohnson', 'pass', 4, 'Bob', 'Johnson', '789 Admin Blvd, Washington DC'),
('33445566', 'grad.secretary@example.com', 'gradsecretary', 'pass', 5, 'Grad', 'Secretary', '103 Grad Secretary Rd, University Town'),
('11223344', 'pvora@example.com', 'pvora', 'pass', 3, 'Poorvi', 'Vora', '101 Faculty Ln, University Town'),
('22334455', 'parmer@example.com', 'gparmer', 'pass', 3, 'Gabriel', 'Parmer', '102 Faculty Ln, University Town'),
('11111111', 'hachoi@example.edu', 'hachoi', 'pass', 3, 'Hyeong-Ah', 'Choi', '104 Faculty Dr, University Town'),
('22222222', 'bnarahari@example.edu', 'bnarahari', 'pass', 3, 'Bhagirath', 'Narahari', '105 Faculty Dr, University Town'),
('33333333', 'heller@example.com', 'heller', 'pass', 3, 'John', 'Heller', '106 Faculty Dr, University Town'),
('44444444', 'twood@example.com', 'wood', 'pass', 3, 'Tim', 'Wood', '107 Faculty Ave, University Town'),
('55555555', 'paul.mccartney@example.com', 'pmccartney', 'pass', 2, 'Paul', 'McCartney', '123 Student Ave, Washington DC'),
('66666666', 'george.harrison@example.com', 'gharrison', 'pass', 2, 'George', 'Harrison', '456 Student Ave, Washington DC'),
('88888880', 'ringo.starr@example.com', 'rstarr', 'pass', 2, 'Ringo', 'Starr', '789 Beatle Blvd, Washington DC'),
('88888888', 'bholiday@example.edu', 'bholiday', 'pass', 2, 'Billie', 'Holiday', '2222 I St NW Washington, D.C'),
('99999999', 'dkrall@example.edu', 'dkrall', 'pass', 2, 'Diana', 'Krall', '2222 I St NW Washington, D.C'),
('77777777', 'eric.clapton@example.com', 'eclapton', 'pass', 6, 'Eric', 'Clapton', '104 Rock Rd, Washington DC'),
('12312312', 'john.lennon@example.com', 'jlennon', 'pass', 1, 'John', 'Lennon', '123 Abbey Road, Liverpool, UK'),
('66666667', 'ringo.starr2@example.com', 'rstarr2', 'pass', 1, 'Ringo', 'Starr', '456 Abbey Road, Liverpool, UK'),
('10101010', 'test@example.com', 'test', 'pass', 2, 'Marcell', 'Ambush', '510 Barlow Two Taverns');

-- admin
INSERT INTO admin (uid) VALUES 
('34567890');

-- gs
INSERT INTO grad_secretary (uid) VALUES 
('33445566');

-- our faculty
INSERT INTO faculty (uid, d_num, is_advisor, is_instructor, is_reviewer, is_cac) VALUES
('11223344', 1, TRUE, TRUE, TRUE, FALSE),
('22334455', 1, TRUE, TRUE, FALSE, FALSE),
('11111111', 1, TRUE, TRUE, TRUE, TRUE),
('22222222', 1, TRUE, TRUE, TRUE, FALSE),
('33333333', 1, FALSE, TRUE, TRUE, FALSE),
('44444444', 1, FALSE, FALSE, TRUE, FALSE);

-- graduate students
INSERT INTO grad_student (uid, advisor_uid, d_num, program, credit_hours, gpa, is_suspended, has_advising_hold, form1_submitted, form1_approved, matriculation_date) VALUES
('55555555', '22222222', 1, 'MS in Computer Science', 30, 3.50, FALSE, FALSE, TRUE, TRUE, '2023-08-15'),
('66666666', '22334455', 1, 'MS in Computer Science', 30, 2.90, FALSE, FALSE, TRUE, TRUE, '2023-08-15'),
('88888880', '22334455', 1, 'PhD in Computer Science', 36, 4.00, FALSE, FALSE, TRUE, TRUE, '2022-08-15'),
('88888888', '11111111', 1, 'MS in Computer Science', 24, 3.70, FALSE, FALSE, TRUE, TRUE, '2023-08-15'),
('99999999', '22222222', 1, 'MS in Computer Science', 27, 3.20, FALSE, FALSE, TRUE, TRUE, '2023-08-15'),
('10101010', '22222222', 1, 'MS in Computer Science', 27, 3.20, FALSE, TRUE, FALSE, FALSE, '2025-08-15');
-- alumni
INSERT INTO alumni (uid, graduation_semester, degree) VALUES
('77777777', 'Spring 2014', 'MS in Computer Science');

-- our applicants 
INSERT INTO applicant (uid, semester, ssn, degree_sought, gre_verbal, gre_quant, gre_year, work_experience, areas_of_interest, transcript_received, status) VALUES
('12312312', 'Fall 2024', '111-11-1111', 'PhD', 160, 165, 2023, '5 years at Apple Records', 'Computer Vision, Machine Learning', TRUE, 'under review'),
('66666667', 'Fall 2024', '222-11-1111', 'MS', 155, 160, 2023, '3 years at EMI Studios', 'Software Engineering, Database Systems', FALSE, 'incomplete');


-- gre 
INSERT INTO gre_subject (applicant_uid, subject, score, year) VALUES
('12312312', 'Computer Science', 800, 2023),
('12312312', 'Mathematics', 750, 2023);

-- prior degrees
INSERT INTO prior_degree (applicant_uid, degree_type, year, gpa, university) VALUES
('12312312', 'Bachelors', 2018, 3.8, 'Liverpool University'),
('12312312', 'Masters', 2020, 3.9, 'Cambridge University'),
('66666667', 'Bachelors', 2019, 3.5, 'London University');

-- recommendation letters
INSERT INTO recommendation_letter (applicant_uid, writer_name, writer_email, writer_title, institution_name, letter_content, is_submitted, submission_date) VALUES
('12312312', 'Paul McCartney', 'paul.mccartney@example.com', 'Professor of Computer Science', 'Liverpool University', 'John is an exceptional student with strong research potential in computer vision. His work at Apple Records demonstrates his ability to apply machine learning concepts in real-world scenarios. I strongly recommend him for the PhD program.', TRUE, '2024-01-15'),
('12312312', 'George Harrison', 'george.harrison@example.com', 'Associate Professor', 'Oxford University', 'John has shown remarkable aptitude for research during his time working with me. His analytical skills and dedication make him an excellent candidate for your PhD program.', TRUE, '2024-01-20'),
('12312312', 'Ringo Starr', 'ringo.starr@example.com', 'Senior Lecturer', 'Manchester University', 'I have known John for several years and can attest to his strong technical skills and work ethic. He would be an asset to your program.', FALSE, NULL),
('66666667', 'John Lennon', 'john.lennon@example.com', 'Professor', 'Cambridge University', 'Ringo has demonstrated solid foundational knowledge in software engineering and shows promise for graduate study.', FALSE, NULL);

-- reccomendation letters
INSERT INTO recommendation_letter_review (letter_id, reviewer_id, rating, is_generic, is_credible) VALUES
(1, '11111111', 5, 'N', 'Y'),
(1, '22222222', 4, 'N', 'Y'),
(2, '11111111', 4, 'N', 'Y');

--revieiwng applications 
INSERT INTO review (applicant_uid, reviewer_id, rating, deficiency_courses, reject_reasons, comment, recommended_advisor, decision) VALUES
('12312312', '11111111', 3, NULL, NULL, 'Excellent candidate with strong research potential', '11223344', 'Admit with Aid'),
('12312312', '22222222', 2, 'Algorithms, Operating Systems', NULL, 'Strong but needs to complete deficiency courses', '22334455', 'Admit'),
('66666667', '33333333', 1, NULL, 'B,C', 'Weak GRE scores and limited research experience', NULL, 'Reject');

-- SCHEDULE SCHEMAA
INSERT INTO schedule (crn, section_num, semester, time, day, room_num, max_enrollment, instructor_uid) VALUES
(6221, 1, 'Spring 25', '1500—1730', 'M', 'SEH 1300', 50, '11111111'),
(6220, 1, 'Spring 25', '1600—1830', 'W', 'SEH 1300', 50, '33333333'),
(6461, 1, 'Spring 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
(6212, 1, 'Spring 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
(6232, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '11111111'),
(6233, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '22222222'),
(6241, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6242, 1, 'Spring 25', '1800—2030', 'R', 'SEH 1300', 50, '11111111'),
(6246, 1, 'Spring 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
(6251, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '33333333'),
(6254, 1, 'Spring 25', '1530—1800', 'M', 'SEH 1300', 50, '11111111'),
(6260, 1, 'Spring 25', '1800—2030', 'R', 'SEH 1300', 50, '22222222'),
(6262, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6283, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '11111111'),
(6284, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
(6286, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6384, 1, 'Spring 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
(6243, 1, 'Spring 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
(6244, 1, 'Spring 25', '1800—2030', 'T', 'SEH 1300', 50, '33333333'),
(6210, 1, 'Spring 25', '1800—2030', 'W', 'SEH 1300', 50, '11111111'),
(6339, 1, 'Spring 25', '1600—1830', 'R', 'SEH 1300', 50, '22222222'),
(6325, 1, 'Spring 25', '1600—1830', 'R', 'SEH 1300', 50, '33333333'),
(6325, 1, 'Fall 25', '1600—1830', 'R', 'SEH 1300', 50, '33333333'),
(6221, 1, 'Fall 25', '1500—1730', 'M', 'SEH 1300', 50, '11111111'),
(6220, 1, 'Fall 25', '1600—1830', 'W', 'SEH 1300', 50, '33333333'),
(6461, 1, 'Fall 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
(6212, 1, 'Fall 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
(6232, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '11111111'),
(6233, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '22222222'),
(6241, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6242, 1, 'Fall 25', '1800—2030', 'R', 'SEH 1300', 50, '11111111'),
(6246, 1, 'Fall 25', '1500—1730', 'T', 'SEH 1300', 50, '22222222'),
(6251, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '33333333'),
(6254, 1, 'Fall 25', '1530—1800', 'M', 'SEH 1300', 50, '11111111'),
(6260, 1, 'Fall 25', '1800—2030', 'R', 'SEH 1300', 50, '22222222'),
(6262, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6283, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '11111111'),
(6284, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
(6286, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '33333333'),
(6384, 1, 'Fall 25', '1500—1730', 'W', 'SEH 1300', 50, '11111111'),
(6243, 1, 'Fall 25', '1800—2030', 'M', 'SEH 1300', 50, '22222222'),
(6244, 1, 'Fall 25', '1800—2030', 'T', 'SEH 1300', 50, '33333333'),
(6210, 1, 'Fall 25', '1800—2030', 'W', 'SEH 1300', 50, '11111111'),
(6339, 1, 'Fall 25', '1600—1830', 'R', 'SEH 1300', 50, '22222222');

-- TRANSCRIPTS 
INSERT INTO transcript (student_uid, crn, semester, grade) VALUES
-- paul mccaartney's courses
('55555555', 6221, 'Fall 2023', 'A'),
('55555555', 6212, 'Fall 2023', 'A'),
('55555555', 6461, 'Fall 2023', 'A'),
('55555555', 6232, 'Fall 2023', 'A'),
('55555555', 6233, 'Fall 2023', 'A'),
('55555555', 6241, 'Fall 2023', 'B'),
('55555555', 6246, 'Fall 2023', 'B'),
('55555555', 6262, 'Fall 2023', 'B'),
('55555555', 6283, 'Fall 2023', 'B'),
('55555555', 6242, 'Fall 2023', 'B'),

--george harrison courses
('66666666', 6243, 'Fall 2023', 'C'),
('66666666', 6221, 'Fall 2023', 'B'),
('66666666', 6461, 'Fall 2023', 'B'),
('66666666', 6212, 'Fall 2023', 'B'),
('66666666', 6232, 'Fall 2023', 'B'),
('66666666', 6233, 'Fall 2023', 'B'),
('66666666', 6241, 'Fall 2023', 'B'),
('66666666', 6242, 'Fall 2023', 'B'),
('66666666', 6283, 'Fall 2023', 'B'),
('66666666', 6284, 'Fall 2023', 'B'),

-- ringo starr courses
('88888880', 6221, 'Fall 2023', 'A'),
('88888880', 6461, 'Fall 2023', 'A'),
('88888880', 6212, 'Fall 2023', 'A'),
('88888880', 6220, 'Fall 2023', 'A'),
('88888880', 6232, 'Fall 2023', 'A'),
('88888880', 6233, 'Fall 2023', 'A'),
('88888880', 6241, 'Fall 2023', 'A'),
('88888880', 6242, 'Fall 2023', 'A'),
('88888880', 6246, 'Fall 2023', 'A'),
('88888880', 6260, 'Fall 2023', 'A'),
('88888880', 6251, 'Fall 2023', 'A'),
('88888880', 6254, 'Fall 2023', 'A'),

-- eric clapton alumni data
('77777777', 6221, 'Spring 2014', 'B'),
('77777777', 6212, 'Spring 2014', 'B'),
('77777777', 6461, 'Spring 2014', 'B'),
('77777777', 6232, 'Spring 2014', 'B'),
('77777777', 6233, 'Spring 2014', 'B'),
('77777777', 6241, 'Spring 2014', 'B'),
('77777777', 6242, 'Spring 2014', 'B'),
('77777777', 6283, 'Spring 2014', 'A'),
('77777777', 6284, 'Spring 2014', 'A'),
('77777777', 6286, 'Spring 2014', 'A');



--ADVISING AND GRAD DATA 
INSERT INTO form_courses (student_uid, crn, semester_planned) VALUES
-- paul mccartney's form 1
('55555555', 6220, 'Spring 2024'),
('55555555', 6251, 'Spring 2024'),
('55555555', 6286, 'Spring 2024'),
('55555555', 6325, 'Fall 2024'),

-- ringo starr's form 1
('88888880', 6325, 'Spring 2024'),
('88888880', 6339, 'Spring 2024'),
('88888880', 6384, 'Spring 2024'),
('88888880', 6286, 'Fall 2024');


-- thesis information
INSERT INTO thesis (student_uid, title, abstract, submission_date, advisor_uid) VALUES
('88888880', 'Advanced Cryptographic Protocols for Distributed Systems', 'This thesis explores novel cryptographic approaches for securing distributed systems in edge computing environments.', '2024-03-15', '22334455');
