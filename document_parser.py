import PyPDF2
from docx import Document
import json

def extract_text_from_file(file_path, filename):
    """Reads raw text from PDF, DOCX, TXT, MD, or JSON files."""
    text = ""
    ext = filename.rsplit('.', 1)[1].lower()
    
    try:
        if ext in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
        elif ext == 'json':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    text = json.dumps(data, indent=2)
            except json.JSONDecodeError as e:
                return f"[FORMAT_ERROR: Invalid JSON Syntax. {str(e)}]"
                
        elif ext == 'docx':
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            
        elif ext == 'pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
    except Exception as e:
        text = f"[ERROR READING FILE: {filename}]"

    return text