import os
import re
import fitz  # PyMuPDF
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3MB limit

# Extract text from PDF in memory
def extract_text_from_pdf(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    return " ".join(page.get_text() for page in doc).strip()

# Split into manageable chunks for the API
def split_text(text, max_words=150):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

# Send to Grok API and get raw flashcard text
def generate_flashcards(text_chunk):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a flashcard generator. Output Q&A flashcards only."},
            {"role": "user", "content": f"Generate flashcards from this text:\n{text_chunk}"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    try:
        res = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=15)
        if res.ok:
            return res.json()["choices"][0]["message"]["content"]
        return f"[Error {res.status_code}]: {res.text}"
    except Exception as e:
        return f"[API Error]: {e}"

# Parse Q&A from raw text
def parse_flashcards(raw_text):
    qa_pairs = re.findall(r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\nQ:|\Z)", raw_text, re.DOTALL)
    return [{"question": q.strip(), "answer": a.strip()} for q, a in qa_pairs]

# Route
@app.route("/", methods=["GET", "POST"])
def index():
    flashcards = []
    error = None

    if request.method == "POST":
        pdf = request.files.get("pdf")
        if not pdf or not pdf.filename.lower().endswith(".pdf"):
            error = "Please upload a valid PDF file."
            return render_template("index.html", flashcards=[], error=error)

        try:
            text = extract_text_from_pdf(pdf.read())
        except Exception:
            error = "Failed to read the PDF file."
            return render_template("index.html", flashcards=[], error=error)

        if not text:
            error = "PDF has no readable text."
            return render_template("index.html", flashcards=[], error=error)

        chunks = split_text(text)
        for chunk in chunks[:3]:  # Limit to first 3 chunks
            raw = generate_flashcards(chunk)
            if raw.startswith("[Error"):
                error = raw
                return render_template("index.html", flashcards=[], error=error)
            flashcards.extend(parse_flashcards(raw))

    return render_template("index.html", flashcards=flashcards, error=error)

if __name__ == "__main__":
    app.run(debug=True)