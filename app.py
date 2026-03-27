from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import tempfile
import shutil
import json
import uuid
import copy

from document_parser import extract_text_from_file
from llm_engine import grade_entire_exam

app = Flask(__name__)
app.secret_key = 'gitam-auto-evaluator-2026-secret'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'json'}

# ============================================================
# DEMO CREDENTIALS
# ============================================================
VALID_CREDENTIALS = {
    '1352': 'Praneel@123'
}

# ============================================================
# DEMO DATA — Bundles and Students
# ============================================================
BUNDLES = [
    {
        'id': 'bundle-1',
        'code': 'CSEN3083',
        'name': 'Deep Learning – Theory & Applications',
        'exam_type': 'Offline Exam',
        'exam_date': '10 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-1', 'name': 'Rahul Sharma', 'reg_no': 'REG2023001', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-2', 'name': 'Priya Patel', 'reg_no': 'REG2023002', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-3', 'name': 'Arun Kumar', 'reg_no': 'REG2023003', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-4', 'name': 'Sneha Reddy', 'reg_no': 'REG2023004', 'evaluated': False, 'marks_obtained': 0},
        ]
    },
    {
        'id': 'bundle-2',
        'code': 'CSEN2092',
        'name': 'OOSE Based Application Development',
        'exam_type': 'Offline Exam',
        'exam_date': '09 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-5', 'name': 'Vikas Kushwaha', 'reg_no': 'REG2023005', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-6', 'name': 'Ananya Singh', 'reg_no': 'REG2023006', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-7', 'name': 'Mohammed Ali', 'reg_no': 'REG2023007', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-8', 'name': 'Lakshmi Narayanan', 'reg_no': 'REG2023008', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-9', 'name': 'Deepak Verma', 'reg_no': 'REG2023009', 'evaluated': False, 'marks_obtained': 0},
        ]
    },
    {
        'id': 'bundle-3',
        'code': 'MKTG1001',
        'name': 'Marketing Management Fundamentals',
        'exam_type': 'Offline Exam',
        'exam_date': '16 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-10', 'name': 'Kavya Menon', 'reg_no': 'REG2023010', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-11', 'name': 'Rohit Jain', 'reg_no': 'REG2023011', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-12', 'name': 'Fatima Begum', 'reg_no': 'REG2023012', 'evaluated': False, 'marks_obtained': 0},
        ]
    },
    {
        'id': 'bundle-4',
        'code': 'CSEN3011',
        'name': 'Artificial Neural Networks',
        'exam_type': 'Offline Exam',
        'exam_date': '06 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-13', 'name': 'Arjun Nair', 'reg_no': 'REG2023013', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-14', 'name': 'Meera Iyer', 'reg_no': 'REG2023014', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-15', 'name': 'Siddharth Gupta', 'reg_no': 'REG2023015', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-16', 'name': 'Pooja Deshmukh', 'reg_no': 'REG2023016', 'evaluated': False, 'marks_obtained': 0},
        ]
    },
    {
        'id': 'bundle-5',
        'code': 'CSEN2031',
        'name': 'Artificial Intelligence (2026 Batch)',
        'exam_type': 'Offline Exam',
        'exam_date': '05 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-17', 'name': 'Nikhil Rao', 'reg_no': 'REG2023017', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-18', 'name': 'Divya Kapoor', 'reg_no': 'REG2023018', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-19', 'name': 'Rajesh Pillai', 'reg_no': 'REG2023019', 'evaluated': False, 'marks_obtained': 0},
        ]
    },
    {
        'id': 'bundle-6',
        'code': 'CSEN3071',
        'name': 'Web Application Development',
        'exam_type': 'Offline Exam',
        'exam_date': '04 Feb, 2026',
        'duration': '1 hr 30 min',
        'total_marks': 30,
        'students': [
            {'id': 'stu-20', 'name': 'Tanvi Bhatt', 'reg_no': 'REG2023020', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-21', 'name': 'Karthik Sundaram', 'reg_no': 'REG2023021', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-22', 'name': 'Ishaan Malhotra', 'reg_no': 'REG2023022', 'evaluated': False, 'marks_obtained': 0},
            {'id': 'stu-23', 'name': 'Nandini Saxena', 'reg_no': 'REG2023023', 'evaluated': False, 'marks_obtained': 0},
        ]
    }
]

# In-memory store for uploaded texts and AI results per session
uploaded_data = {}  # { 'bundle-1': { 'key_text': '...', 'students': { 'stu-1': { 'answer_text': '...', 'ai_result': {...} } } } }


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_bundle(bundle_id):
    for b in BUNDLES:
        if b['id'] == bundle_id:
            return b
    return None


def get_student(bundle, student_id):
    for s in bundle['students']:
        if s['id'] == student_id:
            return s
    return None


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll = request.form.get('roll_number', '').strip()
        password = request.form.get('password', '').strip()

        if roll in VALID_CREDENTIALS and VALID_CREDENTIALS[roll] == password:
            session['logged_in'] = True
            session['lecturer_id'] = roll
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid Roll Number or Password. Please try again.')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template('dashboard.html',
                           bundles=BUNDLES,
                           lecturer_id=session.get('lecturer_id', 'Lecturer'))


@app.route('/bundle/<bundle_id>')
def bundle_detail(bundle_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    bundle = get_bundle(bundle_id)
    if not bundle:
        return redirect(url_for('dashboard'))

    return render_template('bundle.html',
                           bundle=bundle,
                           lecturer_id=session.get('lecturer_id', 'Lecturer'))


@app.route('/evaluate/<bundle_id>/<student_id>')
def evaluate(bundle_id, student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    bundle = get_bundle(bundle_id)
    if not bundle:
        return redirect(url_for('dashboard'))

    student = get_student(bundle, student_id)
    if not student:
        return redirect(url_for('bundle_detail', bundle_id=bundle_id))

    # Get any previously uploaded texts
    bundle_data = uploaded_data.get(bundle_id, {})
    key_text = bundle_data.get('key_text', '')
    student_data = bundle_data.get('students', {}).get(student_id, {})
    student_text = student_data.get('answer_text', '')
    ai_result = student_data.get('ai_result', None)

    return render_template('evaluate.html',
                           bundle=bundle,
                           student=student,
                           student_text=student_text,
                           key_text=key_text,
                           ai_result=ai_result,
                           lecturer_id=session.get('lecturer_id', 'Lecturer'))


@app.route('/upload_files', methods=['POST'])
def upload_files():
    """Upload key and/or answer files for a bundle."""
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    bundle_id = request.form.get('bundle_id')
    key_file = request.files.get('key_file')
    answer_file = request.files.get('answer_file')

    if not bundle_id:
        return jsonify({'status': 'error', 'message': 'No bundle ID provided.'})

    if bundle_id not in uploaded_data:
        uploaded_data[bundle_id] = {'key_text': '', 'students': {}}

    messages = []

    if key_file and allowed_file(key_file.filename):
        temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{key_file.filename}")
        key_file.save(temp_path)
        text = extract_text_from_file(temp_path, key_file.filename)
        try:
            os.remove(temp_path)
        except:
            pass
        uploaded_data[bundle_id]['key_text'] = text
        messages.append('Evaluation key uploaded')

    if answer_file and allowed_file(answer_file.filename):
        temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{answer_file.filename}")
        answer_file.save(temp_path)
        text = extract_text_from_file(temp_path, answer_file.filename)
        try:
            os.remove(temp_path)
        except:
            pass
        # Store as a generic answer for the bundle — individual student answers are stored per student
        messages.append('Answer sheet uploaded')

    if not messages:
        return jsonify({'status': 'error', 'message': 'No valid files were provided.'})

    return jsonify({'status': 'success', 'message': ' & '.join(messages) + ' successfully.'})


@app.route('/upload_single', methods=['POST'])
def upload_single():
    """Upload a single file (answer or key) and return the extracted text."""
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    file = request.files.get('file')
    bundle_id = request.form.get('bundle_id')
    student_id = request.form.get('student_id', '')
    file_type = request.form.get('type')  # 'answer' or 'key'

    if not file or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file. Use PDF, DOCX, or TXT.'})

    temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    file.save(temp_path)
    text = extract_text_from_file(temp_path, file.filename)
    try:
        os.remove(temp_path)
    except:
        pass

    if text.startswith('[ERROR') or text.startswith('[FORMAT_ERROR'):
        return jsonify({'status': 'error', 'message': 'Could not extract text from this file.'})

    if len(text.strip()) < 5:
        return jsonify({'status': 'error', 'message': 'File appears to be empty or unreadable.'})

    # Store the text in memory
    if bundle_id not in uploaded_data:
        uploaded_data[bundle_id] = {'key_text': '', 'students': {}}

    if file_type == 'key':
        uploaded_data[bundle_id]['key_text'] = text
    elif file_type == 'answer' and student_id:
        if student_id not in uploaded_data[bundle_id]['students']:
            uploaded_data[bundle_id]['students'][student_id] = {}
        uploaded_data[bundle_id]['students'][student_id]['answer_text'] = text

    return jsonify({'status': 'success', 'text': text})


@app.route('/ai_evaluate', methods=['POST'])
def ai_evaluate():
    """Run Gemini AI evaluation on student answer vs key."""
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    data = request.get_json()
    bundle_id = data.get('bundle_id')
    student_id = data.get('student_id')

    if not bundle_id or not student_id:
        return jsonify({'status': 'error', 'message': 'Missing bundle or student ID.'})

    bundle_data = uploaded_data.get(bundle_id, {})
    key_text = bundle_data.get('key_text', '')
    student_data = bundle_data.get('students', {}).get(student_id, {})
    student_text = student_data.get('answer_text', '')

    if not key_text:
        return jsonify({'status': 'error', 'message': 'No evaluation key uploaded. Please upload the key first.'})

    if not student_text:
        return jsonify({'status': 'error', 'message': 'No student answer sheet found. Please upload it first.'})

    # Call the Gemini engine
    result = grade_entire_exam(
        teacher_text=key_text,
        student_text=student_text,
        strictness='Normal',
        feedback_style='Detailed'
    )

    # Store AI result
    uploaded_data[bundle_id]['students'][student_id]['ai_result'] = result

    # Update student status in BUNDLES (demo data)
    bundle = get_bundle(bundle_id)
    if bundle:
        student = get_student(bundle, student_id)
        if student:
            student['evaluated'] = True
            student['marks_obtained'] = result.get('total_awarded', 0)

    return jsonify(result)


@app.route('/save_marks', methods=['POST'])
def save_marks():
    """Save the lecturer's final marks."""
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    data = request.get_json()
    bundle_id = data.get('bundle_id')
    student_id = data.get('student_id')
    total = data.get('total', 0)

    bundle = get_bundle(bundle_id)
    if bundle:
        student = get_student(bundle, student_id)
        if student:
            student['evaluated'] = True
            student['marks_obtained'] = total

    return jsonify({'status': 'success', 'message': 'Marks saved.'})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)