from flask import Flask, render_template, request, send_file
from llm_engine import evaluate_answer
import pandas as pd
import os
import tempfile
from collections import Counter

# --- IMPORT THE TIER 3 PARSER ---
from document_parser import extract_text_from_file, parse_teacher_key, parse_student_exam

app = Flask(__name__)

# ==========================================
# 🛡️ SECURITY CONFIGURATIONS
# ==========================================
# 1. The Elevator Weight Limit: Cap uploads at 5 Megabytes max
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

# 2. The ID Checker: Only allow these exact file types
ALLOWED_EXTENSIONS = {'csv', 'pdf', 'docx'}

def allowed_file(filename):
    """Returns True if the file has an extension and it is in our allowed list."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================

# --- TIER 1: HYBRID SINGLE STUDENT GRADING ---
@app.route("/", methods=["GET", "POST"])
def home():
    results = None
    if request.method == "POST":
        teacher_ans = request.form.get("teacher_answer")
        student_ans = request.form.get("student_answer")
        
        # 1. Get AI allocated marks
        ai_marks = float(request.form.get("ai_marks", 5))
        
        # 2. DYNAMICALLY catch all manual parameters selected by the teacher
        manual_params = {}
        for key, value in request.form.items():
            if key.startswith("check_"):
                mark_key = key.replace("check_", "mark_")
                mark_val = request.form.get(mark_key)
                if mark_val and float(mark_val) > 0:
                    param_name = value 
                    manual_params[param_name] = float(mark_val)
                    
        total_manual_marks = sum(manual_params.values())
        grand_total_marks = ai_marks + total_manual_marks
        
        raw_concepts = request.form.get("concepts", "")
        concepts = [c.strip() for c in raw_concepts.split(",") if c.strip()]
        
        # 3. Run the AI Engine ONLY on the AI allocated marks
        ai_results = evaluate_answer(teacher_ans, student_ans, concepts, ai_marks)
        
        # 4. Package everything together for the frontend
        results = {
            "ai_eval": ai_results,
            "manual_params": manual_params,
            "total_manual_marks": total_manual_marks,
            "grand_total_marks": grand_total_marks
        }
        
    return render_template("index.html", results=results, active_tab='single')

# --- TIER 2: BULK CSV GRADING & DASHBOARD ---
@app.route("/bulk", methods=["POST"])
def bulk_grade():
    file = request.files.get("csv_file")
    teacher_ans = request.form.get("bulk_teacher_answer")
    total_marks = float(request.form.get("bulk_total_marks"))
    
    raw_concepts = request.form.get("bulk_concepts", "")
    concepts = [c.strip() for c in raw_concepts.split(",") if c.strip()]

    # 🛡️ SECURITY CHECK: Is there a file, and is it a CSV?
    if not file or file.filename == '':
        return "Security Alert: No file uploaded!", 400
    if not allowed_file(file.filename) or not file.filename.endswith('.csv'):
        return "Security Alert: Invalid file type! Only .csv files are allowed.", 400

    df = pd.read_csv(file)
    awarded_marks_list = []
    feedback_list = []
    all_missing_concepts = [] 
    
    for index, row in df.iterrows():
        student_ans = str(row.get('Student_Answer', ''))
        res = evaluate_answer(teacher_ans, student_ans, concepts, total_marks)
        
        awarded_marks_list.append(res['awarded_marks'])
        all_missing_concepts.extend(res['missing_concepts'])
        
        feedback = f"Match: {res['semantic_similarity']}%. "
        if res['missing_concepts']:
            feedback += f"Missing: {', '.join(res['missing_concepts'])}. "
        else:
            feedback += "All concepts found! "
            
        if res['irrelevant_sentences']:
            feedback += f"Fluff detected: {len(res['irrelevant_sentences'])} sentence(s)."
            
        feedback_list.append(feedback.strip())

    df['Awarded_Marks'] = awarded_marks_list
    df['AI_Feedback'] = feedback_list

    output_path = "graded_results.csv"
    df.to_csv(output_path, index=False)

    total_students = len(df)
    avg_score = round(sum(awarded_marks_list) / total_students, 1) if total_students > 0 else 0
    
    dist = {"0-20%": 0, "21-40%": 0, "41-60%": 0, "61-80%": 0, "81-100%": 0}
    for mark in awarded_marks_list:
        p = (mark / total_marks) * 100
        if p <= 20: dist["0-20%"] += 1
        elif p <= 40: dist["21-40%"] += 1
        elif p <= 60: dist["41-60%"] += 1
        elif p <= 80: dist["61-80%"] += 1
        else: dist["81-100%"] += 1

    concept_counts = Counter(all_missing_concepts)
    
    bulk_results = {
        "total_students": total_students,
        "average_score": avg_score,
        "total_marks": total_marks,
        "dist_labels": list(dist.keys()),
        "dist_data": list(dist.values()),
        "concept_labels": list(concept_counts.keys()),
        "concept_data": list(concept_counts.values())
    }

    return render_template("index.html", bulk_results=bulk_results, active_tab='bulk')

# --- TIER 3: FULL EXAM DOCUMENT GRADING ---
@app.route("/exam", methods=["POST"])
def grade_exam():
    teacher_file = request.files.get("teacher_doc")
    student_file = request.files.get("student_doc")

    # 🛡️ SECURITY CHECK: Ensure files exist and are the correct type
    if not teacher_file or not student_file:
        return "Security Alert: Missing files!", 400
    if not allowed_file(teacher_file.filename) or not allowed_file(student_file.filename):
        return "Security Alert: Invalid file type! Only .pdf and .docx are allowed.", 400

    # Save uploaded files temporarily so Python can read them
    temp_dir = tempfile.gettempdir()
    teacher_path = os.path.join(temp_dir, teacher_file.filename)
    student_path = os.path.join(temp_dir, student_file.filename)
    
    teacher_file.save(teacher_path)
    student_file.save(student_path)

    # Extract raw text and parse into dictionaries
    teacher_text = extract_text_from_file(teacher_path, teacher_file.filename)
    student_text = extract_text_from_file(student_path, student_file.filename)

    teacher_data = parse_teacher_key(teacher_text)
    student_data = parse_student_exam(student_text)

    # Clean up the temporary files
    os.remove(teacher_path)
    os.remove(student_path)

    # Grade the exam question by question
    exam_results = []
    total_exam_marks = 0
    total_awarded_marks = 0

    for q_id, t_info in teacher_data.items():
        s_ans = student_data.get(q_id, "") 
        
        res = evaluate_answer(
            t_info['answer'], 
            s_ans, 
            t_info['concepts'], 
            t_info['marks']
        )
        
        total_exam_marks += t_info['marks']
        total_awarded_marks += res['awarded_marks']

        res['question_id'] = q_id
        res['student_answer'] = s_ans
        exam_results.append(res)

    # Package the final report for the UI
    final_report = {
        "total_awarded": round(total_awarded_marks, 1),
        "total_possible": total_exam_marks,
        "percentage": round((total_awarded_marks / total_exam_marks) * 100, 1) if total_exam_marks > 0 else 0,
        "question_breakdown": exam_results
    }

    return render_template("index.html", exam_report=final_report, active_tab='exam')

# --- DOWNLOAD ROUTE ---
@app.route("/download")
def download_csv():
    return send_file("graded_results.csv", as_attachment=True, download_name="Graded_Class_Results.csv")

if __name__ == "__main__":
    print("Starting Secure Flask Web Server...")
    # 🛡️ SECURITY: Debug mode is now OFF to hide code from the public
    app.run(debug=False)