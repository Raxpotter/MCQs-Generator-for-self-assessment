from flask import Flask, render_template, request, make_response
from flask_bootstrap import Bootstrap
import spacy
from collections import Counter
import random
from PyPDF2 import PdfReader

app = Flask(__name__, static_folder='static')
Bootstrap(app)

nlp = spacy.load("en_core_web_sm")


def generate_mcqs(text, num_questions=5):
    if text is None or not text.strip():
        return []

    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    num_questions = min(num_questions, len(sentences))
    selected_sentences = random.sample(sentences, num_questions)
    mcqs = []
    skipped_sentences = 0

    for sentence in selected_sentences:
        sent_doc = nlp(sentence)
        nouns = [token.text for token in sent_doc if token.pos_ == "NOUN"]

        if not nouns:
            skipped_sentences += 1
            continue

        subject = random.choice(nouns)
        question_stem = sentence.replace(subject, "______")

        distractors = list(set(nouns) - {subject})
        while len(distractors) < 3:
            distractors.append("None")

        random.shuffle(distractors)
        answer_choices = [subject] + distractors[:3]
        random.shuffle(answer_choices)

        correct_answer = chr(65 + answer_choices.index(subject))
        mcqs.append((question_stem, answer_choices, correct_answer))

        if len(mcqs) == num_questions:
            break

    print(f"Skipped sentences: {skipped_sentences}")
    return mcqs


def process_pdf(file):
    text = ""
    pdf_reader = PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = ""

        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            for file in files:
                if file.filename.endswith('.pdf'):
                    text += process_pdf(file)
                elif file.filename.endswith('.txt'):
                    text += file.read().decode('utf-8')
        else:
            text = request.form.get('text', "")

        num_questions = int(request.form.get('num_questions', 5))

        mcqs = generate_mcqs(text, num_questions=num_questions)
        mcqs_with_index = [(i + 1, mcq) for i, mcq in enumerate(mcqs)]

        response = make_response(render_template('mcqs.html', mcqs=mcqs_with_index))
        response.set_cookie('mcqs', str(mcqs_with_index))
        return response

    return render_template('index.html')


@app.route('/results', methods=['POST'])
def results():
    mcqs = eval(request.cookies.get('mcqs', '[]'))  # Retrieve MCQs from cookies
    correct_count = 0
    user_answers = []

    for i, (index, mcq) in enumerate(mcqs):
        question, choices, correct_answer = mcq
        user_answer_index = request.form.get(f'answer-{i + 1}', 'N/A')
        
        # Get the actual answer choice text based on the index
        if user_answer_index != 'N/A':
            user_answer = choices[ord(user_answer_index) - 65]  # Convert 'A', 'B', etc. to list index
        else:
            user_answer = 'No Answer'

        correct_answer_text = choices[ord(correct_answer) - 65]  # Same for correct answer
        
        is_correct = user_answer == correct_answer_text
        if is_correct:
            correct_count += 1
        
        # Append the full answers to the list
        user_answers.append((question, choices, correct_answer_text, user_answer, is_correct))

    total_questions = len(mcqs)
    score = f"{correct_count}/{total_questions}"
    
    # Pass user_answers and score to the template
    return render_template('results.html', score=score, user_answers=user_answers)

if __name__ == '__main__':
    app.run(debug=True)
