"""
database.py
------------
Handles all database setup and connections using plain sqlite3.
No ORM is used so the flow is easy to explain in a viva/demo:
Flask route -> SQL query -> sqlite3 file (internship_portal.db)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "internship_portal.db")


def get_db_connection():
    """Create a new DB connection with rows accessible like dictionaries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't already exist. Also creates a default admin."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table: stores students, admins, and managers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'admin', 'manager')),
            roll_number TEXT,
            branch TEXT,
            phone TEXT,
            cgpa TEXT,
            resume_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Internships table: one row per internship record
    cur.execute("""
        CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            submission_status TEXT NOT NULL DEFAULT 'Draft'
                CHECK(submission_status IN ('Draft', 'Submitted')),
            
            company_name TEXT NOT NULL,
            company_location TEXT,
            company_website TEXT,
            role TEXT,
            start_date TEXT,
            end_date TEXT,
            internship_type TEXT,
            stipend TEXT,
            mode TEXT,
            domain TEXT,
            
            manager_id INTEGER,
            manager_name TEXT,
            manager_email TEXT,

            -- Status of the internship LETTER itself: Pending or Submitted
            letter_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(letter_status IN ('Pending', 'Submitted')),
            letter_filename TEXT,

            -- Completion letter & Report
            completion_filename TEXT,
            completion_status TEXT NOT NULL DEFAULT 'Not Uploaded'
                CHECK(completion_status IN ('Not Uploaded', 'Uploaded')),
            report_filename TEXT,
            report_status TEXT NOT NULL DEFAULT 'Not Uploaded'
                CHECK(report_status IN ('Not Uploaded', 'Uploaded')),

            -- Feedback and evaluation
            manager_feedback TEXT,
            feedback_rating INTEGER CHECK(feedback_rating BETWEEN 1 AND 5),
            tech_skills INTEGER CHECK(tech_skills BETWEEN 1 AND 5),
            communication INTEGER CHECK(communication BETWEEN 1 AND 5),
            teamwork INTEGER CHECK(teamwork BETWEEN 1 AND 5),
            problem_solving INTEGER CHECK(problem_solving BETWEEN 1 AND 5),
            professionalism INTEGER CHECK(professionalism BETWEEN 1 AND 5),
            strengths TEXT,
            improvements TEXT,

            -- Overall review status
            review_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(review_status IN ('Pending', 'Under Review', 'Approved', 'Rejected', 'Correction Required', 'Ongoing', 'Completed')),
            
            admin_remarks TEXT,

            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            event_type TEXT NOT NULL DEFAULT 'Internship Drive',
            role TEXT,
            eligibility TEXT,
            stipend TEXT,
            mode TEXT DEFAULT 'On-Campus',
            location TEXT,
            deadline TEXT,
            description TEXT,
            link TEXT,
            status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'Closed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            resume_filename TEXT,
            student_note TEXT,
            status TEXT DEFAULT 'Applied' CHECK(status IN ('Applied', 'Under Review', 'Shortlisted', 'Selected', 'Rejected')),
            admin_notes TEXT,
            interview_date TEXT,
            interview_time TEXT,
            interview_venue TEXT,
            interview_instructions TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(event_id, student_id)
        )
    """)

    conn.commit()

    # Seed one default admin account so there's something to log in with immediately
    cur.execute("SELECT * FROM users WHERE role = 'admin' LIMIT 1")
    if cur.fetchone() is None:
        from werkzeug.security import generate_password_hash
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("T&P Admin", "admin@university.edu", generate_password_hash("admin123"), "admin")
        )
        conn.commit()

    conn.close()
