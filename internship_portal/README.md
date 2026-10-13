# Training & Placement Internship Portal

A Flask-based web application for a college T&P (Training & Placement) cell
to track student internship letters, completion letters, and manager feedback.

## Tech Stack (Framework)

| Layer          | Technology                                  |
|----------------|----------------------------------------------|
| Backend        | Python 3, Flask                              |
| Database       | SQLite (via built-in `sqlite3` module)       |
| Templating     | Jinja2 (bundled with Flask)                  |
| Auth           | Flask sessions + Werkzeug password hashing   |
| Frontend       | Bootstrap 5, Font Awesome (via CDN)          |
| File uploads   | Flask's `request.files` + `secure_filename`  |

No ORM or extra auth library is used, so every database query and every
login check is plain, readable Python — good for explaining line-by-line
in a viva.

## Folder Structure

```
internship_portal/
├── app.py                 # All routes / application logic
├── database.py            # DB schema (users, internships) + connection helper
├── requirements.txt
├── templates/              # Jinja2 HTML pages
│   ├── base.html            # Shared layout, navbar, flash messages
│   ├── index.html            # Landing page
│   ├── register.html         # Student registration
│   ├── login.html
│   ├── student_dashboard.html
│   ├── new_internship.html
│   ├── admin_dashboard.html
│   └── view_internship.html
├── static/css/style.css
└── uploads/
    ├── letters/            # Uploaded internship letters
    └── completion/         # Uploaded completion letters
```

## Database Design

**users**
- id, full_name, email, password_hash, role (student/admin), roll_number, branch

**internships** (one row per internship a student adds)
- id, student_id (FK -> users)
- company_name, role, start_date, end_date
- letter_status (Pending / Submitted), letter_filename
- completion_status (Not Uploaded / Uploaded), completion_filename
- manager_feedback, feedback_rating (1-5)
- review_status (Under Review / Approved / Rejected)

## User Flows

**Student**
1. Register / Login
2. Add an internship record (company name, letter status, upload letter PDF)
3. Later, upload the completion letter once the internship ends
4. View T&P's feedback and approval status

**Admin (T&P Officer)**
1. Login with the seeded admin account
2. See dashboard: totals, pending vs submitted letters, completions
3. Filter by review status (Under Review / Approved / Rejected)
4. Open a student's record, view uploaded documents, write feedback,
   give a 1-5 rating, and set Approved/Rejected

## How to Run

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The database (`internship_portal.db`) and an admin account are created
automatically the first time you run the app.

**Default admin login:**
- Email: `admin@university.edu`
- Password: `admin123`

## Possible Extensions (mention these in your presentation as "future scope")

- Email notifications when feedback is added
- Export reports to Excel/PDF for placement statistics
- Multiple admin roles (Department Coordinator vs Placement Officer)
- Deadline reminders for pending letters
- Company-wise / branch-wise analytics dashboard with charts
