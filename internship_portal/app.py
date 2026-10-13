"""
app.py
------
Main Flask application for the Training & Placement Internship Portal.

FRAMEWORK OVERVIEW (for your presentation):
  1. Flask        -> Web framework (routes, request handling, templating)
  2. sqlite3       -> Lightweight database, no server needed
  3. Jinja2        -> Templating engine (comes bundled with Flask) for HTML
  4. Werkzeug      -> Password hashing + safe file name handling (comes with Flask)
  5. Sessions      -> Used to keep a user logged in (session['user_id'])

FOLDER STRUCTURE:
  internship_portal/
  ├── app.py                <- routes / application logic (this file)
  ├── database.py           <- DB schema + connection helper
  ├── templates/             <- all HTML pages (Jinja2)
  ├── static/css/style.css   <- styling
  └── uploads/
        ├── letters/         <- uploaded internship letters
        └── completion/      <- uploaded completion letters
"""

import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_db_connection, init_db

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_LETTERS = os.path.join(BASE_DIR, 'uploads', 'letters')
UPLOAD_COMPLETION = os.path.join(BASE_DIR, 'uploads', 'completion')
UPLOAD_REPORTS = os.path.join(BASE_DIR, 'uploads', 'reports')
UPLOAD_RESUMES = os.path.join(BASE_DIR, 'uploads', 'resumes')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_LETTERS, exist_ok=True)
os.makedirs(UPLOAD_COMPLETION, exist_ok=True)
os.makedirs(UPLOAD_REPORTS, exist_ok=True)
os.makedirs(UPLOAD_RESUMES, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Auth helper decorators
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session['role'] == 'admin' else 'student_dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        roll_number = request.form.get('roll_number', '').strip()
        branch = request.form.get('branch', '').strip()

        if not full_name or not email or not password:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('An account with this email already exists.', 'danger')
            conn.close()
            return redirect(url_for('register'))

        conn.execute(
            'INSERT INTO users (full_name, email, password_hash, role, roll_number, branch) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (full_name, email, generate_password_hash(password), 'student', roll_number, branch)
        )
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f"Welcome, {user['full_name']}!", 'success')
            return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'student_dashboard'))

        flash('Invalid email or password.', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()

    # Fetch latest 3 open events and check if this student has applied
    events = conn.execute('''
        SELECT events.*,
               ea.status as app_status,
               ea.applied_at,
               ea.interview_date,
               ea.interview_time,
               ea.interview_venue,
               ea.interview_instructions,
               CASE WHEN ea.id IS NOT NULL THEN 1 ELSE 0 END as applied
        FROM events
        LEFT JOIN event_applications ea ON events.id = ea.event_id AND ea.student_id = ?
        WHERE events.status = 'Open'
        ORDER BY events.created_at DESC LIMIT 3
    ''', (session['user_id'],)).fetchall()

    # Fetch any shortlisted interviews for this student
    shortlisted_interviews = conn.execute('''
        SELECT ea.*, events.title as event_title, events.company_name, events.role, events.mode, events.location
        FROM event_applications ea
        JOIN events ON ea.event_id = events.id
        WHERE ea.student_id = ? AND ea.status = 'Shortlisted'
        ORDER BY ea.applied_at DESC
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template(
        'student_dashboard.html',
        internship=internship,
        events=events,
        shortlisted_interviews=shortlisted_interviews
    )


@app.route('/student/internship', methods=['GET', 'POST'])
@login_required
def student_internship():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()

    if request.method == 'POST':
        internship_id = request.form.get('internship_id')
        company_name = request.form.get('company_name', '').strip()
        role = request.form.get('role', '').strip()
        domain = request.form.get('domain', '').strip()
        mode = request.form.get('mode', 'Offline')
        internship_type = request.form.get('internship_type', 'Paid')
        stipend = request.form.get('stipend', '').strip()
        company_location = request.form.get('company_location', '').strip()
        company_website = request.form.get('company_website', '').strip()
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        manager_name = request.form.get('manager_name', '').strip()
        manager_email = request.form.get('manager_email', '').strip()

        submit_action = request.form.get('submit_action', 'draft')
        submission_status = 'Submitted' if submit_action == 'submit' else 'Draft'

        letter_filename = None
        file = request.files.get('letter_file')
        if file and file.filename and allowed_file(file.filename):
            letter_filename = secure_filename(f"{session['user_id']}_{file.filename}")
            file.save(os.path.join(UPLOAD_LETTERS, letter_filename))

        if internship_id:
            # Update existing record
            cur_record = conn.execute('SELECT * FROM internships WHERE id = ? AND student_id = ?', (internship_id, session['user_id'])).fetchone()
            if not cur_record:
                conn.close()
                abort(404)

            final_letter = letter_filename if letter_filename else cur_record['letter_filename']
            letter_status = 'Submitted' if final_letter else cur_record['letter_status']

            # If student was in 'Correction Required', re-submitting changes review_status back to 'Pending'
            new_review_status = 'Pending' if submission_status == 'Submitted' else cur_record['review_status']

            conn.execute('''
                UPDATE internships SET
                    company_name = ?, role = ?, domain = ?, mode = ?, internship_type = ?,
                    stipend = ?, company_location = ?, company_website = ?, start_date = ?, end_date = ?,
                    manager_name = ?, manager_email = ?, submission_status = ?, review_status = ?,
                    letter_filename = ?, letter_status = ?
                WHERE id = ? AND student_id = ?
            ''', (
                company_name, role, domain, mode, internship_type,
                stipend, company_location, company_website, start_date, end_date,
                manager_name, manager_email, submission_status, new_review_status,
                final_letter, letter_status, internship_id, session['user_id']
            ))
            conn.commit()
            flash('Internship details updated successfully.', 'success')
        else:
            # Insert new record
            letter_status = 'Submitted' if letter_filename else 'Pending'
            conn.execute('''
                INSERT INTO internships (
                    student_id, company_name, role, domain, mode, internship_type,
                    stipend, company_location, company_website, start_date, end_date,
                    manager_name, manager_email, submission_status, review_status,
                    letter_status, letter_filename
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['user_id'], company_name, role, domain, mode, internship_type,
                stipend, company_location, company_website, start_date, end_date,
                manager_name, manager_email, submission_status, 'Pending',
                letter_status, letter_filename
            ))
            conn.commit()
            flash('Internship registered successfully.', 'success')

        conn.close()
        return redirect(url_for('student_internship'))

    # GET request
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()

    edit_mode = (request.args.get('edit') == '1') or (internship is None)
    return render_template('student_internship.html', internship=internship, edit_mode=edit_mode)


@app.route('/student/internship/submit', methods=['POST'])
@login_required
def student_internship_submit():
    if session.get('role') != 'student':
        abort(403)
    conn = get_db_connection()
    conn.execute('''
        UPDATE internships SET submission_status = 'Submitted', review_status = 'Pending'
        WHERE student_id = ?
    ''', (session['user_id'],))
    conn.commit()
    conn.close()
    flash('Your internship has been submitted for Training & Placement verification.', 'success')
    return redirect(url_for('student_internship'))


@app.route('/student/documents')
@login_required
def student_documents():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    return render_template('student_documents.html', internship=internship)


@app.route('/student/documents/upload/<string:doc_type>', methods=['POST'])
@login_required
def student_upload_document(doc_type):
    if session.get('role') != 'student':
        abort(403)

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()

    if not internship:
        conn.close()
        flash('Please register your internship details first.', 'warning')
        return redirect(url_for('student_internship'))

    file = request.files.get('doc_file')
    if not file or not file.filename or not allowed_file(file.filename):
        conn.close()
        flash('Please select a valid file (PDF, JPG, or PNG).', 'danger')
        return redirect(url_for('student_documents'))

    if doc_type == 'letter':
        filename = secure_filename(f"{session['user_id']}_letter_{file.filename}")
        file.save(os.path.join(UPLOAD_LETTERS, filename))
        conn.execute('UPDATE internships SET letter_filename = ?, letter_status = ? WHERE id = ?', (filename, 'Submitted', internship['id']))
        flash('Offer / Approval letter uploaded successfully.', 'success')
    elif doc_type == 'completion':
        filename = secure_filename(f"{session['user_id']}_completion_{file.filename}")
        file.save(os.path.join(UPLOAD_COMPLETION, filename))
        conn.execute('UPDATE internships SET completion_filename = ?, completion_status = ? WHERE id = ?', (filename, 'Uploaded', internship['id']))
        flash('Completion certificate uploaded successfully.', 'success')
    elif doc_type == 'report':
        filename = secure_filename(f"{session['user_id']}_report_{file.filename}")
        file.save(os.path.join(UPLOAD_REPORTS, filename))
        conn.execute('UPDATE internships SET report_filename = ?, report_status = ? WHERE id = ?', (filename, 'Uploaded', internship['id']))
        flash('Final project report uploaded successfully.', 'success')
    else:
        conn.close()
        abort(400)

    conn.commit()
    conn.close()
    return redirect(url_for('student_documents'))


@app.route('/student/progress')
@login_required
def student_progress():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    return render_template('student_progress.html', internship=internship)


@app.route('/student/feedback')
@login_required
def student_feedback():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    return render_template('student_feedback.html', internship=internship)


@app.route('/student/completion')
@login_required
def student_completion():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    internship = conn.execute(
        'SELECT * FROM internships WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    return render_template('student_completion.html', internship=internship)


@app.route('/student/events')
@login_required
def student_events():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    events = conn.execute('''
        SELECT events.*,
               ea.status as app_status,
               ea.applied_at,
               ea.admin_notes,
               ea.interview_date,
               ea.interview_time,
               ea.interview_venue,
               ea.interview_instructions,
               CASE WHEN ea.id IS NOT NULL THEN 1 ELSE 0 END as applied
        FROM events
        LEFT JOIN event_applications ea ON events.id = ea.event_id AND ea.student_id = ?
        ORDER BY events.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('student_events.html', events=events)


@app.route('/student/events/<int:event_id>/apply', methods=['POST'])
@login_required
def student_apply_event(event_id):
    if session.get('role') != 'student':
        abort(403)

    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        abort(404)

    # Check if already applied
    existing = conn.execute('SELECT id FROM event_applications WHERE event_id = ? AND student_id = ?', (event_id, session['user_id'])).fetchone()
    if existing:
        conn.close()
        flash('You have already applied for this event.', 'info')
        return redirect(url_for('student_events'))

    # Check for resume upload or fallback to user profile resume
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    resume_filename = user['resume_filename']

    file = request.files.get('resume_file')
    if file and file.filename and allowed_file(file.filename):
        resume_filename = secure_filename(f"{session['user_id']}_app_{file.filename}")
        file.save(os.path.join(UPLOAD_RESUMES, resume_filename))

    student_note = request.form.get('student_note', '').strip()

    conn.execute('''
        INSERT INTO event_applications (event_id, student_id, resume_filename, student_note, status)
        VALUES (?, ?, ?, ?, 'Applied')
    ''', (event_id, session['user_id'], resume_filename, student_note))

    # Send confirmation notification to student
    conn.execute('''
        INSERT INTO notifications (user_id, message)
        VALUES (?, ?)
    ''', (session['user_id'], f"You successfully applied for {event['title']} at {event['company_name']}."))

    conn.commit()
    conn.close()
    flash(f"Application for '{event['title']}' submitted successfully!", 'success')
    return redirect(url_for('student_events'))


@app.route('/student/notifications')
@login_required
def student_notifications():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    notifications = conn.execute(
        'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('student_notifications.html', notifications=notifications)


@app.route('/student/notifications/read', methods=['POST'])
@login_required
def student_mark_notifications_read():
    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('student_notifications'))


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        branch = request.form.get('branch', '').strip()
        phone = request.form.get('phone', '').strip()
        cgpa = request.form.get('cgpa', '').strip()

        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        resume_filename = user['resume_filename']

        file = request.files.get('resume_file')
        if file and file.filename and allowed_file(file.filename):
            resume_filename = secure_filename(f"{session['user_id']}_resume_{file.filename}")
            file.save(os.path.join(UPLOAD_RESUMES, resume_filename))

        conn.execute('''
            UPDATE users SET full_name = ?, roll_number = ?, branch = ?, phone = ?, cgpa = ?, resume_filename = ?
            WHERE id = ?
        ''', (full_name, roll_number, branch, phone, cgpa, resume_filename, session['user_id']))
        conn.commit()
        session['full_name'] = full_name
        flash('Profile and resume updated successfully.', 'success')

    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('student_profile.html', user=user)


# ---------------------------------------------------------------------------
# Admin (T&P Officer) routes
# ---------------------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    active_tab = request.args.get('tab', 'verifications')
    status_filter = request.args.get('status', 'All')
    search_query = request.args.get('search', '').strip()

    conn = get_db_connection()

    # 1. Fetch verifications data
    query = '''
        SELECT internships.*, users.full_name, users.roll_number, users.branch, users.email
        FROM internships
        JOIN users ON internships.student_id = users.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter != 'All':
        query += ' AND internships.review_status = ?'
        params.append(status_filter)
        
    if search_query:
        query += ' AND (users.full_name LIKE ? OR internships.company_name LIKE ? OR users.branch LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY internships.submitted_at DESC'
    records = conn.execute(query, tuple(params)).fetchall()

    # Quick stats
    total = conn.execute('SELECT COUNT(*) c FROM internships').fetchone()['c']
    submitted = conn.execute("SELECT COUNT(*) c FROM internships WHERE letter_status='Submitted'").fetchone()['c']
    pending = conn.execute("SELECT COUNT(*) c FROM internships WHERE letter_status='Pending'").fetchone()['c']
    completed = conn.execute("SELECT COUNT(*) c FROM internships WHERE completion_status='Uploaded'").fetchone()['c']
    stats = {'total': total, 'submitted': submitted, 'pending': pending, 'completed': completed}

    # 2. Fetch all pushed events with applicant count
    events = conn.execute('''
        SELECT events.*, COUNT(event_applications.id) as applicant_count
        FROM events
        LEFT JOIN event_applications ON events.id = event_applications.event_id
        GROUP BY events.id
        ORDER BY events.created_at DESC
    ''').fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        records=records,
        stats=stats,
        status_filter=status_filter,
        search_query=search_query,
        active_tab=active_tab,
        events=events
    )


@app.route('/admin/events/push', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_push_event():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company_name = request.form.get('company_name', '').strip()
        event_type = request.form.get('event_type', 'Internship Drive')
        role = request.form.get('role', '').strip()
        eligibility = request.form.get('eligibility', '').strip()
        stipend = request.form.get('stipend', '').strip()
        mode = request.form.get('mode', 'Hybrid')
        location = request.form.get('location', '').strip()
        deadline = request.form.get('deadline', '').strip()
        description = request.form.get('description', '').strip()
        link = request.form.get('link', '').strip()
        broadcast = request.form.get('broadcast_notification')

        if not title or not company_name or not description:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin_push_event'))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO events (title, company_name, event_type, role, eligibility, stipend, mode, location, deadline, description, link, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open')
        ''', (title, company_name, event_type, role, eligibility, stipend, mode, location, deadline, description, link))

        # Broadcast notification to all students if checked
        if broadcast:
            students = conn.execute("SELECT id FROM users WHERE role = 'student'").fetchall()
            for s in students:
                conn.execute('''
                    INSERT INTO notifications (user_id, message)
                    VALUES (?, ?)
                ''', (s['id'], f"📢 New T&P Drive: '{title}' by {company_name}! Apply before {deadline or 'deadline'}."))

        conn.commit()
        conn.close()
        flash(f"Event '{title}' pushed successfully and is now visible to all students!", 'success')
        return redirect(url_for('admin_dashboard', tab='events'))

    return render_template('admin_push_event.html')


@app.route('/admin/events/<int:event_id>')
@login_required
@admin_required
def admin_event_detail(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        abort(404)

    # Fetch applicants with user details
    applications = conn.execute('''
        SELECT ea.*, users.full_name, users.email, users.roll_number, users.branch, users.phone, users.cgpa
        FROM event_applications ea
        JOIN users ON ea.student_id = users.id
        WHERE ea.event_id = ?
        ORDER BY ea.applied_at DESC
    ''', (event_id,)).fetchall()

    conn.close()
    return render_template('admin_event_detail.html', event=event, applications=applications)


@app.route('/admin/events/<int:event_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def admin_toggle_event_status(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        abort(404)

    new_status = 'Closed' if event['status'] == 'Open' else 'Open'
    conn.execute('UPDATE events SET status = ? WHERE id = ?', (new_status, event_id))
    conn.commit()
    conn.close()
    flash(f"Event status updated to {new_status}.", 'info')
    return redirect(url_for('admin_event_detail', event_id=event_id))


@app.route('/admin/applications/<int:application_id>/status', methods=['POST'])
@login_required
@admin_required
def admin_update_application_status(application_id):
    status = request.form.get('status', 'Applied')
    admin_notes = request.form.get('admin_notes', '').strip()
    interview_date = request.form.get('interview_date', '').strip()
    interview_time = request.form.get('interview_time', '').strip()
    interview_venue = request.form.get('interview_venue', '').strip()
    interview_instructions = request.form.get('interview_instructions', '').strip()

    conn = get_db_connection()
    app_record = conn.execute('''
        SELECT ea.*, events.title as event_title, events.company_name
        FROM event_applications ea
        JOIN events ON ea.event_id = events.id
        WHERE ea.id = ?
    ''', (application_id,)).fetchone()

    if not app_record:
        conn.close()
        abort(404)

    conn.execute('''
        UPDATE event_applications SET
            status = ?,
            admin_notes = ?,
            interview_date = ?,
            interview_time = ?,
            interview_venue = ?,
            interview_instructions = ?
        WHERE id = ?
    ''', (status, admin_notes, interview_date, interview_time, interview_venue, interview_instructions, application_id))

    # Send tailored status update notification to the applicant
    if status == 'Shortlisted':
        msg = f"🎉 Shortlisted for Interview! Application for '{app_record['event_title']}' ({app_record['company_name']}) has been shortlisted."
        if interview_date:
            msg += f" Date: {interview_date}"
            if interview_time:
                msg += f" at {interview_time}"
        if interview_venue:
            msg += f" | Venue/Link: {interview_venue}"
        if interview_instructions:
            msg += f" | Instructions: {interview_instructions}"
    elif status == 'Selected':
        msg = f"🏆 Congratulations! You have been SELECTED for '{app_record['event_title']}' at {app_record['company_name']}! {admin_notes}"
    else:
        msg = f"📢 Application Update: Your application for '{app_record['event_title']}' is now '{status}'."
        if admin_notes:
            msg += f" Note: {admin_notes}"

    conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)', (app_record['student_id'], msg))

    conn.commit()
    conn.close()
    flash(f"Applicant status updated to '{status}' and notification sent.", 'success')
    return redirect(url_for('admin_event_detail', event_id=app_record['event_id']))


@app.route('/admin/internship/<int:internship_id>')
@login_required
@admin_required
def view_internship(internship_id):
    conn = get_db_connection()
    record = conn.execute('''
        SELECT internships.*, users.full_name, users.roll_number, users.branch, users.email
        FROM internships JOIN users ON internships.student_id = users.id
        WHERE internships.id = ?
    ''', (internship_id,)).fetchone()
    conn.close()

    if record is None:
        abort(404)
    return render_template('view_internship.html', record=record)


@app.route('/admin/internship/<int:internship_id>/feedback', methods=['POST'])
@login_required
@admin_required
def give_feedback(internship_id):
    feedback = request.form.get('manager_feedback', '').strip()
    rating = request.form.get('feedback_rating') or None
    review_status = request.form.get('review_status', 'Under Review')
    admin_remarks = request.form.get('admin_remarks', '').strip()

    tech_skills = request.form.get('tech_skills') or None
    communication = request.form.get('communication') or None
    teamwork = request.form.get('teamwork') or None
    problem_solving = request.form.get('problem_solving') or None
    professionalism = request.form.get('professionalism') or None
    strengths = request.form.get('strengths', '').strip()
    improvements = request.form.get('improvements', '').strip()

    conn = get_db_connection()
    conn.execute(
        '''UPDATE internships SET 
            manager_feedback = ?, feedback_rating = ?, review_status = ?, admin_remarks = ?,
            tech_skills = ?, communication = ?, teamwork = ?, problem_solving = ?, professionalism = ?,
            strengths = ?, improvements = ?
           WHERE id = ?''',
        (feedback, rating, review_status, admin_remarks, 
         tech_skills, communication, teamwork, problem_solving, professionalism, strengths, improvements, internship_id)
    )

    # Notify student about review status change or feedback
    internship = conn.execute('SELECT student_id, company_name FROM internships WHERE id = ?', (internship_id,)).fetchone()
    if internship:
        notif_msg = f"Your internship at {internship['company_name']} was updated to '{review_status}' by T&P."
        if admin_remarks:
            notif_msg += f" Remarks: {admin_remarks}"
        conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)', (internship['student_id'], notif_msg))

    conn.commit()
    conn.close()
    flash('Review status and evaluation saved successfully.', 'success')
    return redirect(url_for('view_internship', internship_id=internship_id))


# ---------------------------------------------------------------------------
# File serving routes
# ---------------------------------------------------------------------------
@app.route('/uploads/letters/<path:filename>')
@login_required
def uploaded_letter(filename):
    return send_from_directory(UPLOAD_LETTERS, filename)


@app.route('/uploads/completion/<path:filename>')
@login_required
def uploaded_completion(filename):
    return send_from_directory(UPLOAD_COMPLETION, filename)


@app.route('/uploads/reports/<path:filename>')
@login_required
def uploaded_report(filename):
    return send_from_directory(UPLOAD_REPORTS, filename)


@app.route('/uploads/resumes/<path:filename>')
@login_required
def uploaded_resume(filename):
    return send_from_directory(UPLOAD_RESUMES, filename)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
