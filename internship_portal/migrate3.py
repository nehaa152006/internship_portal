"""
migrate3.py
-----------
Adds tables for the Events / Push Requests & Student Application feature:
- events: Admin pushes internship drives, placement events, or submission requests
- event_applications: Students apply for pushed events/drives, visible to both admin and student
- Adds profile columns (phone, cgpa, resume_filename) to users table if missing.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "internship_portal.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Update users table columns if not present
    existing_cols = [c[1] for c in cur.execute("PRAGMA table_info(users)").fetchall()]
    if 'phone' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        print("Added phone to users")
    if 'cgpa' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN cgpa TEXT")
        print("Added cgpa to users")
    if 'resume_filename' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN resume_filename TEXT")
        print("Added resume_filename to users")

    # 2. Create events table
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
    print("Created events table")

    # 3. Create event_applications table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            resume_filename TEXT,
            student_note TEXT,
            status TEXT DEFAULT 'Applied' CHECK(status IN ('Applied', 'Under Review', 'Shortlisted', 'Selected', 'Rejected')),
            admin_notes TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(event_id, student_id)
        )
    """)
    print("Created event_applications table")

    # Seed sample drives if empty so the portal looks alive immediately
    cur.execute("SELECT COUNT(*) FROM events")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO events (title, company_name, event_type, role, eligibility, stipend, mode, location, deadline, description)
            VALUES 
            (
                'Summer Tech Internship Drive 2026', 
                'Microsoft IDC', 
                'Internship Drive', 
                'Software Engineer Intern', 
                '3rd & 4th Year B.Tech CSE/IT/ECE with CGPA >= 7.5', 
                '₹80,000 / month', 
                'Hybrid', 
                'Hyderabad / Bangalore', 
                '2026-10-30', 
                'Opportunity to work on bleeding-edge cloud and AI systems. Round 1 online coding test followed by technical interviews.'
            ),
            (
                'Urgent: AI/ML Research Internship Request', 
                'Centre for AI Excellence (University T&P)', 
                'T&P Request', 
                'Research & Development Intern', 
                'All branches, proficiency in Python & PyTorch required', 
                '₹25,000 / month (Funded Project)', 
                'On-Campus', 
                'Lab 402, T&P Building', 
                '2026-10-15', 
                'Sponsored 6-month research internship on NLP and Computer Vision. Eligible for academic credit conversion.'
            ),
            (
                'FinTech Full Stack Developer Drive', 
                'Goldman Sachs', 
                'Internship Drive', 
                'Summer Analyst - Engineering', 
                'B.Tech / M.Tech (All engineering disciplines), CGPA >= 7.0', 
                '₹1,00,000 / month', 
                'On-site', 
                'Bangalore', 
                '2026-11-05', 
                'Global markets engineering team internship. Strong data structures and object-oriented programming foundation required.'
            )
        """)
        print("Seeded sample events")

    conn.commit()
    conn.close()
    print("Migration 3 completed successfully!")

if __name__ == '__main__':
    migrate()
