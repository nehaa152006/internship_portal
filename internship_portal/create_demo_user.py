import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "internship_portal.db")

def create_demo_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check existing users
    print("--- Current Users ---")
    users = cur.execute("SELECT id, email, role, full_name FROM users").fetchall()
    for u in users:
        print(f"ID: {u['id']}, Email: {u['email']}, Role: {u['role']}, Name: {u['full_name']}")
    
    # Create demo student
    demo_email = "student@demo.com"
    demo_pass = "student123"
    
    # Check if demo student exists
    existing = cur.execute("SELECT id FROM users WHERE email = ?", (demo_email,)).fetchone()
    
    if not existing:
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role, roll_number, branch) VALUES (?, ?, ?, ?, ?, ?)",
            ("Demo Student", demo_email, generate_password_hash(demo_pass), "student", "12345", "Computer Science")
        )
        conn.commit()
        print(f"\nCreated demo student -> Email: {demo_email}, Password: {demo_pass}")
    else:
        # Update password just in case
        cur.execute("UPDATE users SET password_hash = ? WHERE email = ?", (generate_password_hash(demo_pass), demo_email))
        conn.commit()
        print(f"\nUpdated demo student -> Email: {demo_email}, Password: {demo_pass}")
    
    conn.close()

if __name__ == "__main__":
    create_demo_users()
