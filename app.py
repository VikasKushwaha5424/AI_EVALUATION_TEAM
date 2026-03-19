from flask import Flask, render_template, request, jsonify
import os
import tempfile
import re

from document_parser import extract_text_from_file
from llm_engine import grade_entire_exam

app = Flask(__name__)
# Max file size set to 10MB to handle multi-page PDFs
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def home():
    """Renders the main dashboard."""
    return render_template("index.html")

@app.route("/validate_file", methods=["POST"])
def validate_file():
    """Fast, pre-flight check for file formatting before grading."""
    file = request.files.get("file")
    role = request.form.get("role")
    
    if not file:
        return jsonify({"status": "error", "message": "No file detected."})

    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, file.filename)
    file.save(path)
    text = extract_text_from_file(path, file.filename)
    os.remove(path)

    # 1. Check for broken formats or unreadable PDFs
    if text.startswith("[FORMAT_ERROR"):
        return jsonify({"status": "error", "message": text.replace("[FORMAT_ERROR: ", "").replace("]", "")})
    if text.startswith("[ERROR"):
        return jsonify({"status": "error", "message": "Could not extract text from this file. It might be corrupted."})

    # 2. Strict Check for Teacher Master Key
    if role == "teacher":
        text_lower = text.lower()
        # Ensure the teacher actually assigned marks/points in the document
        if not re.search(r'\b(mark|marks|point|points)\b', text_lower):
            return jsonify({
                "status": "warning", 
                "message": "⚠️ Warning: We couldn't find any 'Marks' or 'Points' assigned in this document. The AI needs to know how much each question is worth!"
            })
        return jsonify({"status": "success", "message": "✅ Format looks good! Marks detected."})

    # 3. Lenient Check for Student File
    if role == "student":
        # Students just need to have *some* text in their document
        if len(text.strip()) < 10:
            return jsonify({"status": "error", "message": "This file appears to be empty."})
        return jsonify({
            "status": "success", 
            "message": "✅ File loaded. (AI will automatically match answers to questions)."
        })

@app.route("/grade_exam", methods=["POST"])
def grade_exam():
    """The main grading pipeline."""
    teacher_file = request.files.get("teacher_doc")
    student_file = request.files.get("student_doc")
    strictness = request.form.get("strictness", "Normal")
    feedback_style = request.form.get("feedback_style", "Detailed")

    # Basic server-side validation just in case they bypass the frontend
    if not teacher_file or not student_file:
        return "Error: Missing files! Please upload both a Master Key and a Student Submission.", 400
    if not allowed_file(teacher_file.filename) or not allowed_file(student_file.filename):
        return "Error: Invalid file type!", 400

    temp_dir = tempfile.gettempdir()
    teacher_path = os.path.join(temp_dir, teacher_file.filename)
    student_path = os.path.join(temp_dir, student_file.filename)
    
    teacher_file.save(teacher_path)
    student_file.save(student_path)

    # Extract raw text from the files
    teacher_raw_text = extract_text_from_file(teacher_path, teacher_file.filename)
    student_raw_text = extract_text_from_file(student_path, student_file.filename)

    # Clean up the temporary files immediately to save space
    os.remove(teacher_path)
    os.remove(student_path)

    # Pass the text to the Gemini God Prompt
    exam_report = grade_entire_exam(
        teacher_text=teacher_raw_text, 
        student_text=student_raw_text, 
        strictness=strictness, 
        feedback_style=feedback_style
    )

    # Pass ONLY the finalized JSON report back to the UI
    return render_template("index.html", exam_report=exam_report)

if __name__ == "__main__":
    app.run(debug=True)