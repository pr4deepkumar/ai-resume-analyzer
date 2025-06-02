import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from openai import OpenAI
import pdfplumber
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

def chat_gpt(conversation):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation
    )
    return response.choices[0].message.content

def pdf_to_text(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
    return text

@app.route('/upload', methods=['GET', 'POST'])
def upload_resume():
    if request.method == 'POST':
        resume_file = request.files.get('file')
        job_description = request.form.get('job_description')
        mandatory_keywords = request.form.get('mandatory_keywords')

        if not resume_file or not job_description or not mandatory_keywords:
            return jsonify({"error": "Missing required fields."}), 400

        filename = secure_filename(resume_file.filename)
        os.makedirs("temp", exist_ok=True)
        temp_path = os.path.join("temp", filename)
        resume_file.save(temp_path)

        resume_text = pdf_to_text(temp_path)
        os.remove(temp_path)

        # GPT Evaluation
        eval_prompt = [
            {"role": "system", "content": "You are a helpful assistant specialized in recruitment and talent management."},
            {"role": "user", "content": f"Mandatory keywords: {mandatory_keywords}"},
            {"role": "user", "content": f"Is this resume suitable for the job? Job description: {job_description}, Resume: {resume_text} (also at the end of the prompt write if the candidate is Suitable, Not Suitable or Maybe Suitable — and the label is mandatory to have)"}
        ]
        comments = chat_gpt(eval_prompt).replace('\n', ' ')

        if "not suitable" in comments.lower():
            suitability = "Not Suitable"
        elif "maybe suitable" in comments.lower():
            suitability = "Maybe Suitable"
        else:
            suitability = "Suitable"

        resume_summary = chat_gpt([
            {"role": "system", "content": "Summarize the resume's key skills, experience, and qualifications."},
            {"role": "user", "content": resume_text}
        ])

        job_summary = chat_gpt([
            {"role": "system", "content": "Summarize the job description's key requirements and responsibilities."},
            {"role": "user", "content": job_description}
        ])

        return jsonify({
            "resume_name": filename,
            "comments": comments.strip(),
            "suitability": suitability,
            "resume_summary": resume_summary.strip(),
            "job_summary": job_summary.strip()
        })

    return render_template('upload.html')

@app.route('/')
def index():
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)