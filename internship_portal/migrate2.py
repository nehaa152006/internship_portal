import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "internship_portal.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Notifications table
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

    # Internships table
    cur.execute("ALTER TABLE internships RENAME TO internships_old_2")
    cur.execute("""
        CREATE TABLE internships (
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

            letter_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(letter_status IN ('Pending', 'Submitted')),
            letter_filename TEXT,

            completion_filename TEXT,
            completion_status TEXT NOT NULL DEFAULT 'Not Uploaded'
                CHECK(completion_status IN ('Not Uploaded', 'Uploaded')),
            report_filename TEXT,
            report_status TEXT NOT NULL DEFAULT 'Not Uploaded'
                CHECK(report_status IN ('Not Uploaded', 'Uploaded')),

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
                CHECK(review_status IN ('Pending', 'Under Review', 'Approved', 'Rejected', 'Correction Required', 'Ongoing', 'Completed')),
            
            admin_remarks TEXT,

            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    cur.execute("""
        INSERT INTO internships (
            id, student_id, submission_status, company_name, role, start_date, end_date, 
            internship_type, mode, domain, manager_id,
            letter_status, letter_filename, completion_filename, completion_status,
            manager_feedback, feedback_rating, tech_skills, communication, teamwork,
            problem_solving, professionalism, strengths, improvements,
            review_status, admin_remarks, submitted_at
        ) 
        SELECT 
            id, student_id, 
            'Submitted', -- Assume existing ones are already submitted
            company_name, role, start_date, end_date, 
            internship_type, mode, domain, manager_id,
            letter_status, letter_filename, completion_filename, completion_status,
            manager_feedback, feedback_rating, tech_skills, communication, teamwork,
            problem_solving, professionalism, strengths, improvements,
            CASE 
                WHEN review_status IN ('Pending', 'Under Review', 'Approved', 'Rejected', 'Ongoing', 'Completed') THEN review_status
                ELSE 'Pending' 
            END,
            admin_remarks, submitted_at 
        FROM internships_old_2
    """)
    cur.execute("DROP TABLE internships_old_2")

    conn.commit()
    conn.close()
    print("Migration 2 successful.")

if __name__ == '__main__':
    migrate()
