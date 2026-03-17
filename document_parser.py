import re
from docx import Document
import PyPDF2

def extract_text_from_file(file_path, filename):
    """Reads raw text from either a DOCX or PDF file."""
    text = ""
    if filename.endswith('.docx'):
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif filename.endswith('.pdf'):
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    return text

def parse_teacher_key(text):
    """
    Parses the teacher's master document.
    Expects format:
    [Q1] Question text...
    [A1] Answer text...
    {Marks: 5}
    {Concepts: a, b}
    """
    questions = {}
    # Split the document by [Q1], [Q2], etc.
    q_blocks = re.split(r'\[Q\d+\]', text)[1:] 
    
    for i, block in enumerate(q_blocks):
        q_id = f"Q{i+1}"
        
        # Extract the Answer part using the new [A1], [A2] tags
        answer_match = re.search(r'\[A\d+\](.*?)(?=\{Marks|\Z)', block, re.DOTALL)
        answer_text = answer_match.group(1).strip() if answer_match else ""
        
        # Extract Marks (supports decimals like 5.5 just in case)
        marks_match = re.search(r'\{Marks:\s*(\d+(\.\d+)?)\}', block)
        marks = float(marks_match.group(1)) if marks_match else 5.0
        
        # Extract Concepts
        concepts_match = re.search(r'\{Concepts:\s*(.*?)\}', block)
        concepts = [c.strip() for c in concepts_match.group(1).split(',')] if concepts_match else []
        
        questions[q_id] = {
            "answer": answer_text,
            "marks": marks,
            "concepts": concepts
        }
    return questions

def parse_student_exam(text):
    """
    Parses the student's document.
    Now looks specifically for [A1], [A2] tags as requested!
    """
    answers = {}
    
    # Finds all instances of [A1] followed by the text until the next [A...] tag
    matches = re.finditer(r'\[A(\d+)\](.*?)(?=\[A\d+\]|\Z)', text, re.DOTALL)
    
    for match in matches:
        q_id = f"Q{match.group(1)}" # Maps [A1] back to Q1, [A2] back to Q2
        student_ans = match.group(2).strip()
        answers[q_id] = student_ans
        
    return answers