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

def parse_teacher_key(raw_text):
    """
    Extracts Question ID, Answer, Concepts, and Marks from the Teacher's text.
    Returns a dictionary: {'Q1': {'answer': '...', 'concepts': [...], 'marks': 5}, ...}
    """
    exam_data = {}
    # Find everything between [Q...] blocks
    blocks = re.split(r'\[(Q\d+)\]', raw_text)[1:] 
    
    for i in range(0, len(blocks), 2):
        q_id = blocks[i].strip()
        content = blocks[i+1]
        
        # Extract Answer
        ans_match = re.search(r'Answer:\s*(.*?)(?=\nConcepts:|$)', content, re.DOTALL)
        # Extract Concepts
        con_match = re.search(r'Concepts:\s*(.*?)(?=\nMarks:|$)', content, re.DOTALL)
        # Extract Marks
        marks_match = re.search(r'Marks:\s*(\d+(\.\d+)?)', content)
        
        if ans_match and con_match and marks_match:
            exam_data[q_id] = {
                'answer': ans_match.group(1).strip(),
                'concepts': [c.strip() for c in con_match.group(1).split(',')],
                'marks': float(marks_match.group(1))
            }
    return exam_data

def parse_student_exam(raw_text):
    """
    Extracts Question ID and Student Answer.
    Returns a dictionary: {'Q1': 'Student answer text...', 'Q2': '...'}
    """
    student_data = {}
    blocks = re.split(r'\[(Q\d+)\]', raw_text)[1:]
    
    for i in range(0, len(blocks), 2):
        q_id = blocks[i].strip()
        content = blocks[i+1]
        
        ans_match = re.search(r'Answer:\s*(.*)', content, re.DOTALL)
        if ans_match:
            student_data[q_id] = ans_match.group(1).strip()
            
    return student_data