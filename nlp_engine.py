import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from spellchecker import SpellChecker
import nltk
from nltk.corpus import wordnet
import sys
import time
import threading
import itertools

# --- 1. SET UP THE LOADING ANIMATION ---
def animate_loading(message):
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    global stop_spinner
    stop_spinner = False
    while not stop_spinner:
        sys.stdout.write(f'\r\033[96m{message} {next(spinner)}\033[0m')
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the line when done
    sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')

nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# Start the spinner animation in the background
print("\n" + "="*50)
t = threading.Thread(target=animate_loading, args=("Booting up AI Models into RAM (This takes about a minute)...",))
t.start()

# --- 2. LOAD THE MODELS (This is the slow part) ---
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')
spell = SpellChecker()

# Stop the spinner
stop_spinner = True
t.join()

print("\033[92m✅ All AI Models loaded successfully!\033[0m")
print("="*50 + "\n")


# --- 3. YOUR EXISTING FUNCTIONS ---
def get_synonyms(word):
    synonyms = set()
    word_formatted = word.replace(' ', '_') 
    for syn in wordnet.synsets(word_formatted):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' ').lower())
    return synonyms

def evaluate_answer(teacher_answer, student_answer, key_concepts, total_marks):
    # --- 1. OVERALL SEMANTIC SIMILARITY ---
    embeddings = model.encode([teacher_answer, student_answer])
    similarity_matrix = cosine_similarity([embeddings[0]], [embeddings[1]])
    semantic_score = similarity_matrix[0][0] 
    
    # --- 2. ADVANCED: SENTENCE-LEVEL FLUFF DETECTION ---
    student_doc = nlp(student_answer) 
    irrelevant_sentences = []
    
    for sent in student_doc.sents:
        sent_text = sent.text.strip()
        if len(sent_text) > 5: 
            sent_emb = model.encode([sent_text])
            sim = cosine_similarity([embeddings[0]], [sent_emb[0]])[0][0]
            
            if sim < 0.25: 
                irrelevant_sentences.append(sent_text)
                
    # --- 3. CONCEPT DETECTION & TYPO TOLERANCE ---
    student_doc_lower = nlp(student_answer.lower())
    corrected_words = []
    for token in student_doc_lower:
        if token.is_alpha: 
            corrected = spell.correction(token.text)
            corrected_words.append(corrected if corrected else token.text)
        else:
            corrected_words.append(token.text)
            
    student_text_corrected = " ".join(corrected_words)
    
    concepts_found = []
    base_concepts_found = [] 
    
    for concept in key_concepts:
        concept_lower = concept.lower()
        
        # Check Direct Match
        if concept_lower in student_text_corrected:
            concepts_found.append(concept)
            base_concepts_found.append(concept)
            continue
            
        # Check Synonym Match
        synonyms = get_synonyms(concept_lower)
        found_synonym = False
        
        for syn in synonyms:
            if syn != concept_lower and syn in student_text_corrected:
                concepts_found.append(f"{concept} (via '{syn}')")
                base_concepts_found.append(concept)
                found_synonym = True
                break 
                
    # --- 4. EXPLAIN MISTAKES: MISSING CONCEPTS ---
    missing_concepts = [c for c in key_concepts if c not in base_concepts_found]

    if len(key_concepts) > 0:
        concept_score = len(concepts_found) / len(key_concepts)
    else:
        concept_score = 1.0 
        
    # --- 5. FINAL CALCULATION ---
    final_score_percentage = (semantic_score * 0.6) + (concept_score * 0.4)
    
    fluff_penalty = len(irrelevant_sentences) * 0.05
    final_score_percentage = max(0, final_score_percentage - fluff_penalty)
    
    awarded_marks = round(final_score_percentage * total_marks, 1)
    awarded_marks = max(0, min(awarded_marks, total_marks))
    
    return {
        "semantic_similarity": round(semantic_score * 100, 1),
        "concepts_found": concepts_found,
        "missing_concepts": missing_concepts,
        "irrelevant_sentences": irrelevant_sentences,
        "concept_score": round(concept_score * 100, 1),
        "awarded_marks": awarded_marks,
        "total_marks": total_marks
    }