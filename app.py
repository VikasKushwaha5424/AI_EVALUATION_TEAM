from flask import Flask, render_template, request, send_file, jsonify
from llm_engine import evaluate_answer, generate_rubric
import pandas as pd
import os
import tempfile
from collections import Counter
from difflib import SequenceMatcher

# Legacy Exam parser
from document_parser import extract_text_from_file, parse_teacher_key, parse_student_exam

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 
ALLOWED_EXTENSIONS = {'csv', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def home():
    # This just loads the empty website when you first open it
    return render_template("index.html")

@app.route("/auto-rubric", methods=["POST"])
def auto_rubric():
    data = request.json
    source_text = data.get("source_text", "")
    if len(source_text.split()) > 1500: return jsonify({"error": "Text too long."}), 400
    return jsonify(generate_rubric(source_text))

# --- THE UNIVERSAL GRADING PIPELINE ---
@app.route("/evaluate", methods=["POST"])
def evaluate_universal():
    # 1. Get the Master Rubric & Options from the new UI
    teacher_ans = request.form.get("teacher_answer")
    total_marks = float(request.form.get("total_marks", 5))
    concepts = [c.strip() for c in request.form.get("concepts", "").split(",") if c.strip()]
    
    strictness = request.form.get("strictness", "Normal")
    feedback_style = request.form.get("feedback_style", "Detailed")

    # 2. Check Input Type (Did they upload a CSV or paste text?)
    csv_file = request.files.get("csv_file")
    student_text = request.form.get("student_answer")

    # --- PATH A: BULK CSV UPLOAD ---
    if csv_file and csv_file.filename:
        if not allowed_file(csv_file.filename) or not csv_file.filename.endswith('.csv'): 
            return "Invalid file type! Please upload a .csv file.", 400
        
        df = pd.read_csv(csv_file)
        awarded_marks_list, feedback_list, all_missing_concepts = [], [], []
        flagged_cheaters = []
        student_records = list(df.iterrows())
        
        for i in range(len(student_records)):
            idx1, row1 = student_records[i]
            ans1 = str(row1.get('Student_Answer', ''))
            
            # Pass new options to the AI
            res = evaluate_answer(teacher_ans, ans1, concepts, total_marks, strictness, feedback_style)
            
            awarded_marks_list.append(res['awarded_marks'])
            all_missing_concepts.extend(res['missing_concepts'])
            feedback_list.append(f"Match: {res['semantic_similarity']}%. " + res['feedback'])
            
            # Anti-Cheat Radar
            for j in range(i + 1, len(student_records)):
                idx2, row2 = student_records[j]
                ans2 = str(row2.get('Student_Answer', ''))
                sim = SequenceMatcher(None, ans1.lower(), ans2.lower()).ratio()
                if sim > 0.85 and len(ans1.split()) > 5:
                    flagged_cheaters.append({
                        "student1": row1.get('Student_ID', f"Row {idx1+2}"), 
                        "student2": row2.get('Student_ID', f"Row {idx2+2}"), 
                        "similarity": round(sim * 100, 1)
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
            "flagged_cheaters": flagged_cheaters
        }
        return render_template("index.html", bulk_results=bulk_results, active_view="results")

    # --- PATH B: SINGLE TEXT ANSWER ---
    elif student_text and student_text.strip():
        res = evaluate_answer(teacher_ans, student_text, concepts, total_marks, strictness, feedback_style)
        return render_template("index.html", single_results=res, active_view="results")

    else:
        return "Please provide either a CSV file or paste a student answer.", 400

# --- PATH C: EXAM GRADER (Kept intact) ---
@app.route("/exam", methods=["POST"])
def grade_exam():
    teacher_file = request.files.get("teacher_doc")
    student_file = request.files.get("student_doc")

    if not teacher_file or not student_file:
        return "Security Alert: Missing files!", 400
    if not allowed_file(teacher_file.filename) or not allowed_file(student_file.filename):
        return "Security Alert: Invalid file type! Only .pdf and .docx are allowed.", 400

    temp_dir = tempfile.gettempdir()
    teacher_path = os.path.join(temp_dir, teacher_file.filename)
    student_path = os.path.join(temp_dir, student_file.filename)
    
    teacher_file.save(teacher_path)
    student_file.save(student_path)

    teacher_text = extract_text_from_file(teacher_path, teacher_file.filename)
    student_text = extract_text_from_file(student_path, student_file.filename)

    teacher_data = parse_teacher_key(teacher_text)
    student_data = parse_student_exam(student_text)

    os.remove(teacher_path)
    os.remove(student_path)

    exam_results = []
    total_exam_marks = 0
    total_awarded_marks = 0

    for q_id, t_info in teacher_data.items():
        s_ans = student_data.get(q_id, "") 
        res = evaluate_answer(
            t_info['answer'], s_ans, t_info['concepts'], t_info['marks'], 
            strictness="Normal", feedback_style="Detailed"
        )
        total_exam_marks += t_info['marks']
        total_awarded_marks += res['awarded_marks']

        res['question_id'] = q_id
        res['student_answer'] = s_ans
        exam_results.append(res)

    final_report = {
        "total_awarded": round(total_awarded_marks, 1),
        "total_possible": total_exam_marks,
        "percentage": round((total_awarded_marks / total_exam_marks) * 100, 1) if total_exam_marks > 0 else 0,
        "question_breakdown": exam_results
    }

    return render_template("index.html", exam_report=final_report, active_view="exam")

@app.route("/download")
def download_csv():
    return send_file("graded_results.csv", as_attachment=True, download_name="Graded_Class_Results.csv")

if __name__ == "__main__":
    app.run(debug=False)