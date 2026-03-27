# 🧠 AI-Based Answer Evaluator (Auto-Evaluator)

An intelligent, local-first Natural Language Processing (NLP) web application designed to automatically evaluate and grade subjective student answers against a teacher's model answer. 

Unlike basic keyword checkers, this engine understands the **semantic meaning** of text, tolerates spelling mistakes, recognizes synonyms, and provides detailed analytics for entire classrooms.

---

## ✨ Key Features

### 1. Intelligent AI Engine
* **Semantic Meaning Detection:** Uses Sentence-BERT to evaluate the actual *meaning* of a student's answer, awarding marks even if they paraphrase the teacher's original text.
* **Fuzzy Concept Matching:** Integrates NLTK WordNet to automatically detect valid synonyms (e.g., accepting "sunshine" when the rubric asks for "sunlight").
* **Typo Tolerance:** Features a built-in spellchecker to ensure students aren't heavily penalized for minor spelling mistakes in key concepts.
* **Fluff Detection:** Identifies and flags highly irrelevant or off-topic sentences ("fluff") within a student's answer.

### 2. Dual-Mode Interface
* **Single Student Deep-Dive:** A quick interface to test individual answers and receive a granular breakdown of semantic matches, found concepts, missing concepts, and irrelevant sentences.
* **Bulk CSV Grading:** Allows a teacher to upload a `.csv` file containing an entire class's answers. The system grades all students instantly and generates a downloadable graded CSV complete with AI-generated feedback sentences.

### 3. Class Insights Dashboard
* Automatically generates a beautiful, interactive dashboard (powered by Chart.js) after a bulk CSV upload.
* Visualizes the **Class Average**, a **Grade Distribution Bar Chart**, and highlights the **Most Missed Concepts** to help teachers identify topics that need reviewing.

---

## 🛠️ Tech Stack & Architecture

This project is built to run 100% locally with zero reliance on paid API keys or cloud AI limits.

* **Backend:** Python, Flask
* **Data Processing:** Pandas
* **Machine Learning & NLP:** * `sentence-transformers` (`all-MiniLM-L6-v2`) for generating 384-dimensional mathematical embeddings.
  * `scikit-learn` for calculating Cosine Similarity between embeddings.
  * `spaCy` (`en_core_web_sm`) for tokenization and sentence boundary detection.
  * `nltk` (WordNet) for synonym generation.
  * `pyspellchecker` for real-time typo correction.
* **Frontend:** HTML5, Bootstrap 5 (Styling), Chart.js (Analytics Visualization)

### The Grading Algorithm
The final awarded mark is calculated using a dynamic weighted system:
* **60% Semantic Similarity:** How closely the overall meaning matches the teacher's model answer.
* **40% Concept Coverage:** The percentage of mandatory key concepts (or their valid synonyms) found in the text.
* **Penalty:** A minor deduction is applied for mathematically irrelevant "fluff" sentences.

---

## 🚀 Installation & Setup Guide

### Prerequisites
* Python 3.8 or higher installed on your machine.
* Git (optional, for cloning).

### Step 1: Clone or Download the Project
Download the source code and navigate into the project directory:
```bash
cd auto-evaluator


Step 2: Create a Virtual Environment
It is highly recommended to use a virtual environment to avoid global dependency conflicts.

For Windows:

Bash
python -m venv venv
venv\Scripts\activate

For Mac/Linux:

Bash
python3 -m venv venv
source venv/bin/activate
Step 3: Install Required Dependencies
With your virtual environment active, install the required Python libraries:

Bash
pip install flask pandas scikit-learn sentence-transformers spacy pyspellchecker nltk
Step 4: Download the spaCy Language Model
Download the English dictionary and grammar rules required by spaCy:

Bash
python -m spacy download en_core_web_sm
Step 5: Run the Application
Start the Flask web server:

Bash
python app.py

(Note: The very first time you run this, it may take a minute or two to automatically download the Sentence-BERT weights in the background. Subsequent runs will be instant).

Open your web browser and navigate to: http://127.0.0.1:5000/

📊 How to Use the Bulk CSV Grader
To grade an entire class at once, navigate to the Bulk CSV Upload tab.

Prepare a .csv file. It must contain the following two exact column headers:

Student_ID

Student_Answer

Enter your Model Answer, Key Concepts (comma-separated), and the Total Marks available.

Upload the .csv file and click Upload & Generate Dashboard.

Review the Class Insights Dashboard, then click Download Graded CSV in the top right corner to get your final grade sheet.




# Qwen2VL-OCR

**Author:** aroky amatthew

A local Gradio web app that extracts text from images in any language using the Qwen2-VL vision-language model, with built-in keyword search.

## Features

- **OCR:** Extracts text in any language from uploaded images using Qwen2-VL-2B-Instruct.
- **Keyword Search:** Search for keywords within the extracted text.
- **GPU Accelerated:** Automatically uses your NVIDIA GPU (float16) for fast inference; falls back to CPU if unavailable.

## Setup

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA drivers (recommended)
- Git

### Installation

1. **Create & activate a virtual environment:**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install PyTorch (GPU):**

   ```powershell
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

   > For CPU-only, use `https://download.pytorch.org/whl/cpu` instead.

3. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Log in to Hugging Face (for model download):**

   ```powershell
   huggingface-cli login
   ```

### Running

```powershell
python app.py
```

Open `http://127.0.0.1:7860` in your browser. Upload an image, optionally enter a keyword, and hit Submit.

## Notes

- First launch downloads ~4 GB of model weights.
- GPU inference takes a few seconds per image; CPU takes 30–120+ seconds.
