## My Program
**University_Registrar_System** is a full-stack academic management system simulating a university registrar. Enabling end-to-end functionality including applicant acceptance, course registration, grade assignment, and graduation processing.

## Important
Upon running the program make sure to press the reset database button on the login page before trying to login to ensure the database is updated upon opening the program.

## Technologies Used
 - Backend: Python (Flask), SQLite
 - Frontend: HTML, CSS, JavaScript
 - Database: SQL (SQLite)

## Features:
- Applicants: Apply to the university, submit personal information, receive admission decisions.
- Course Registration: Enroll in courses after acceptance.
- Grade System: Faculty can assign grades; students can view transcripts.
- Billing: Tuition payment features must be fulfilled before enrollment.
- Graduation: Students can request graduation and become alumni.
- User Roles: Each role has unique permissions and interfaces:
  - Applicants
  - Students
  - Alumni
  - Faculty Members
  - Graduate Secretaries
  - System Administrators
- Secure Login: Protected pages from invalid users accessing information.
- Database Reset Tool: Ability to reset databse from the login page.

## How to run the program

1. **Simply clone the repository:**
   
   git clone https://github.com/dandob1/University_Registrar_System.git

   cd into the folder

2. **Compile and run the project:**

    Use the following command:
   
        python main.py

## How to use the program for full application to graduation
  - Create a new user with the apply to university feature.
  - Once the account is created login with user "11111111" and password "pass" as a faculty advisor.
  - Navigate to the view applications button.
  - View the user you just applied as and approve them to the university by filling out all necessary fields
  - Log back in to the user you created with the UID provided and password you created.
  - Follow instructions on the submit payment button.
  - Login as user "33445566" and password "pass" as a grad secretary
  - Navigate to view applications and matriculate the student you created. Also assign them an advisor from the homepage table's "assign advisor" button.
  - Login as the user you created and submit their advising form for classes they plan to take. Make sure to adhere to all prerequisites and required courses.
  - Approve the advising form from the users faculty advisor page
  - Register for the classes selected in the form from the student homepage
  - Sign in as the grad secretary and provide grades for all of the courses selected. Make sure the GPA is above 3.0 for MS students and above 3.4 for PhD students.
  - If user is a PhD student submit their thesis and approve it just as done with the form.
  - Once all courses have been taken, form/thesis is approved, you can request graduation from the student homepage.
  - Process the graduation from the grad secretary
  - If all requirements have been met and student has successfully graduated, you can sign into their account using the same login and see their admin page
