import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "internship_portal.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Migrate users table
    cur.execute("ALTER TABLE users RENAME TO users_old")
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNswxIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'admin', 'manager')),
            roll_number TEXT,
            branch TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT INTO users (id, full_name, email, password_hash, role, roll_number, branch, created_at) SELECT id, full_name, email, password_hash, role, roll_number, branch, created_at FROM users_old")
    cur.execute("DROP TABLE users_old")

    # 2. Migrate internships table
    cur.execute("ALTER TABLE internships RENAME TO internships_old")
    cur.execute("""
        CREATE TABLE internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            role TEXT,
            start_date TEXT,
            end_date TEXT,
            internship_type TEXT,
            mode TEXT,
            domain TEXT,
            manager_id INTEGER,

            letter_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(letter_status IN ('Pending', 'Submitted')),
            letter_filename TEXT,

            completion_filename TEXT,
            completion_status TEXT NOT NULL DEFAULT 'Not Uploaded'
                CHECK(completion_status IN ('Not Uploaded', 'Uploaded')),

            manager_feedback TEXT,
            feedback_rating INTEGER CHECK(feedback_rating BETWEEN 1 AND 5),
            tech_skills INTEGER CHECK(tech_skills BETWEEN 1 AND 5),
            communication INTEGER CHECK(communication BETWEEN 1 AND 5),
            teamwork INTEGER CHECK(teamwork BETWEEN 1 AND 5),
            problem_solving INTEGER CHECK(problem_solving BETWEEN 1 AND 5),
            professionalism INTEGER CHECK(professionalism BETWEEN 1 AND 5),
            strengths TEXT,
            improvements TEXT,

            review_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(review_status IN ('Pending', 'Under Review', 'Approved', 'Rejected', 'Ongoing', 'Completed')),
            
            admin_remarks TEXT,

            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    # Copy data over
    cur.execute("""
        INSERT INTO internships (
            id, student_id, company_name, role, start_date, end_date, 
            letter_status, letter_filename, completion_filename, completion_status,
            manager_feedback, feedback_rating, review_status, submitted_at
        ) 
        SELECT 
            id, student_id, company_name, role, start_date, end_date, 
            letter_status, letter_filename, completion_filename, completion_status,
            manager_feedback, feedback_rating, 
            CASE 
                WHEN review_status = 'Under Review' THEN 'Under Review'
                WHEN review_status = 'Approved' THEN 'Approved'
                WHEN review_status = 'Rejected' THEN 'Rejected'
                ELSE 'Pending' 
            END,
            submitted_at 
        FROM internships_old
    """)
    cur.execute("DROP TABLE internships_old")

    conn.commit()
    conn.close()
    print("Migration successful.")

if __name__ == '__main__':
    migrate()
