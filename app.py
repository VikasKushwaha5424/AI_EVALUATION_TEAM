from flask import Flask, render_template, request, send_file, jsonify
from llm_engine import evaluate_answer, generate_rubric
import pandas as pd
import os
import tempfile
from collections import Counter
from difflib import SequenceMatcher # Built-in Python library for detecting plagiarism

from document_parser import extract_text_from_file, parse_teacher_key, parse_student_exam

app = Flask(__name__)

# 🛡️ SECURITY CONFIGURATIONS
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 
ALLOWED_EXTENSIONS = {'csv', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- NEW FEATURE: AUTO-RUBRIC API ---
@app.route("/auto-rubric", methods=["POST"])
def auto_rubric():
    data = request.json
    source_text = data.get("source_text", "")
    if len(source_text.split()) > 1500:
        return jsonify({"error": "Text too long. Max 1500 words."}), 400
    rubric = generate_rubric(source_text)
    return jsonify(rubric)

@app.route("/", methods=["GET", "POST"])
def home():
    results = None
    if request.method == "POST":
        teacher_ans = request.form.get("teacher_answer")
        student_ans = request.form.get("student_answer")
        ai_marks = float(request.form.get("ai_marks", 5))
        
        manual_params = {}
        for key, value in request.form.items():
            if key.startswith("check_"):
                mark_key = key.replace("check_", "mark_")
                mark_val = request.form.get(mark_key)
                if mark_val and float(mark_val) > 0:
                    manual_params[value] = float(mark_val)
                    
        total_manual_marks = sum(manual_params.values())
        grand_total_marks = ai_marks + total_manual_marks
        
        raw_concepts = request.form.get("concepts", "")
        concepts = [c.strip() for c in raw_concepts.split(",") if c.strip()]
        
        ai_results = evaluate_answer(teacher_ans, student_ans, concepts, ai_marks)
        
        results = {
            "ai_eval": ai_results,
            "manual_params": manual_params,
            "total_manual_marks": total_manual_marks,
            "grand_total_marks": grand_total_marks
        }
    return render_template("index.html", results=results, active_tab='single')

@app.route("/bulk", methods=["POST"])
def bulk_grade():
    file = request.files.get("csv_file")
    teacher_ans = request.form.get("bulk_teacher_answer")
    total_marks = float(request.form.get("bulk_total_marks"))
    raw_concepts = request.form.get("bulk_concepts", "")
    concepts = [c.strip() for c in raw_concepts.split(",") if c.strip()]

    if not file or file.filename == '':
        return "Security Alert: No file uploaded!", 400
    if not allowed_file(file.filename) or not file.filename.endswith('.csv'):
        return "Security Alert: Invalid file type!", 400

    df = pd.read_csv(file)
    awarded_marks_list = []
    feedback_list = []
    all_missing_concepts = [] 
    
    # NEW FEATURE: ANTI-CHEAT RADAR
    flagged_cheaters = []
    student_records = list(df.iterrows())
    
    for i in range(len(student_records)):
        # 1. Evaluate Student via AI
        idx1, row1 = student_records[i]
        ans1 = str(row1.get('Student_Answer', ''))
        res = evaluate_answer(teacher_ans, ans1, concepts, total_marks)
        
        awarded_marks_list.append(res['awarded_marks'])
        all_missing_concepts.extend(res['missing_concepts'])
        
        feedback = f"Match: {res['semantic_similarity']}%. "
        if res['missing_concepts']: feedback += f"Missing: {', '.join(res['missing_concepts'])}. "
        else: feedback += "All concepts found! "
        if res['irrelevant_sentences']: feedback += f"Fluff detected: {len(res['irrelevant_sentences'])} sentence(s)."
        feedback_list.append(feedback.strip())
        
        # 2. Check for Plagiarism against all other students
        for j in range(i + 1, len(student_records)):
            idx2, row2 = student_records[j]
            ans2 = str(row2.get('Student_Answer', ''))
            
            # If the answers are more than 85% identical and longer than 5 words
            similarity = SequenceMatcher(None, ans1.lower(), ans2.lower()).ratio()
            if similarity > 0.85 and len(ans1.split()) > 5:
                id1 = row1.get('Student_ID', f"Row {idx1+2}")
                id2 = row2.get('Student_ID', f"Row {idx2+2}")
                flagged_cheaters.append({
                    "student1": id1, "student2": id2, "similarity": round(similarity * 100, 1)
                })

    df['Awarded_Marks'] = awarded_marks_list
    df['AI_Feedback'] = feedback_list
    df.to_csv("graded_results.csv", index=False)

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

    bulk_results = {
        "total_students": total_students, "average_score": avg_score, "total_marks": total_marks,
        "dist_labels": list(dist.keys()), "dist_data": list(dist.values()),
        "concept_labels": list(Counter(all_missing_concepts).keys()),
        "concept_data": list(Counter(all_missing_concepts).values()),
        "flagged_cheaters": flagged_cheaters # Send cheat data to UI
    }
    return render_template("index.html", bulk_results=bulk_results, active_tab='bulk')

@app.route("/exam", methods=["POST"])
def grade_exam():
    # ... (Your existing Exam code stays exactly the same) ...
    teacher_file = request.files.get("teacher_doc")
    student_file = request.files.get("student_doc")
    if not teacher_file or not student_file: return "Security Alert: Missing files!", 400
    temp_dir = tempfile.gettempdir()
    teacher_path = os.path.join(temp_dir, teacher_file.filename)
    student_path = os.path.join(temp_dir, student_file.filename)
    teacher_file.save(teacher_path)
    student_file.save(student_path)
    teacher_data = parse_teacher_key(extract_text_from_file(teacher_path, teacher_file.filename))
    student_data = parse_student_exam(extract_text_from_file(student_path, student_file.filename))
    os.remove(teacher_path)
    os.remove(student_path)

    exam_results, total_exam_marks, total_awarded_marks = [], 0, 0
    for q_id, t_info in teacher_data.items():
        s_ans = student_data.get(q_id, "") 
        res = evaluate_answer(t_info['answer'], s_ans, t_info['concepts'], t_info['marks'])
        total_exam_marks += t_info['marks']
        total_awarded_marks += res['awarded_marks']
        res['question_id'] = q_id
        res['student_answer'] = s_ans
        exam_results.append(res)

    final_report = {
        "total_awarded": round(total_awarded_marks, 1), "total_possible": total_exam_marks,
        "percentage": round((total_awarded_marks / total_exam_marks) * 100, 1) if total_exam_marks > 0 else 0,
        "question_breakdown": exam_results
    }
    return render_template("index.html", exam_report=final_report, active_tab='exam')

@app.route("/download")
def download_csv():
    return send_file("graded_results.csv", as_attachment=True, download_name="Graded_Class_Results.csv")

if __name__ == "__main__":
    app.run(debug=False)