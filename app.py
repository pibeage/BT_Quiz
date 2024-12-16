import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from operator import itemgetter

# Flask Configuration
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# Session Configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# Global variables for leaderboard management
leaderboard = []
best_hard_score = None
best_hard_player = None

# Load questions dynamically based on difficulty
def load_questions(difficulty):
    questions_folder = "./questions"
    questions_file = os.path.join(questions_folder, f"questions{difficulty}.txt")
    questions = []
    try:
        with open(questions_file, 'r', encoding='utf-8') as file:
            lines = file.read().strip().split("\n\n")
            for line in lines[:10]:  # Load up to 10 questions
                parts = line.split('\n')
                question = parts[0]
                options = parts[1:5]
                correct_answer = None
                cleaned_options = []
                for option in options:
                    option_text = option.replace('*', '').strip()
                    if '*' in option:
                        correct_answer = option_text
                    cleaned_options.append(option_text)
                questions.append({'question': question, 'options': cleaned_options, 'correct': correct_answer})
    except FileNotFoundError:
        print(f"Warning: Question file {questions_file} not found.")
    return questions

# Helper: Update leaderboard and best "Hard" score
def update_leaderboard(name, score, difficulty):
    global best_hard_score, best_hard_player
    leaderboard.append({'name': name, 'score': score, 'difficulty': difficulty})
    leaderboard.sort(key=lambda x: (x['difficulty'] != 'Hard', -x['score']))

    # Update best "Hard" score
    hard_scores = [entry for entry in leaderboard if entry['difficulty'] == 'Hard']
    if hard_scores:
        best_hard_score = hard_scores[0]['score']
        best_hard_player = hard_scores[0]['name']

# Home Route
@app.route('/')
def home():
    global best_hard_score, best_hard_player

    # Track if start sound was already played
    start_sound_played = session.get('start_sound_played', False)
    if not start_sound_played:
        session['start_sound_played'] = True  # Set to True after first load

    settings = get_user_settings()
    return render_template(
        "index.html",
        best_score=best_hard_score,
        best_player=best_hard_player,
        settings=settings,
        play_start_sound=not start_sound_played  # Pass flag to play sound
    )

# Start Game Route
@app.route('/start_game', methods=['POST'])
def start_game():
    name = request.form['name']
    difficulty = request.form['difficulty']
    questions = load_questions(difficulty)

    if not questions:
        flash("Questions not available for the selected difficulty.", "danger")
        return redirect(url_for('home'))

    session['name'] = name
    session['difficulty'] = difficulty
    session['score'] = 0
    session['question_index'] = 0
    session['questions'] = questions
    return redirect(url_for('play'))

# Play Route
@app.route('/play')
def play():
    if 'question_index' not in session or 'questions' not in session:
        return redirect(url_for('home'))

    question_index = session['question_index']
    questions = session['questions']

    if question_index >= len(questions):
        return redirect(url_for('game_over'))

    question = questions[question_index]
    settings = get_user_settings()  # Retrieve settings here

    return render_template(
        'play.html',
        question=question,
        score=session['score'],
        settings=settings  # Pass settings explicitly to the template
    )

# Submit Answer Route
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    answer = request.form['answer']
    question_index = session['question_index']
    questions = session['questions']

    if question_index < len(questions):
        question = questions[question_index]
        if answer == question['correct']:
            session['score'] += 1

    session['question_index'] += 1
    return redirect(url_for('play'))

# Game Over Route
@app.route('/game_over')
def game_over():
    name = session['name']
    score = session['score']
    difficulty = session['difficulty']

    update_leaderboard(name, score, difficulty)
    current_leaderboard = [entry for entry in leaderboard if entry['difficulty'] == difficulty]

    return render_template(
        'game_over.html',
        score=score,
        leaderboard=current_leaderboard,
        best_score=best_hard_score,
        sounds_enabled=session.get('sounds_enabled', True)
    )

# Settings Route
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        data = request.get_json()
        save_user_settings(data.get('sounds', True), data.get('timer', True), data.get('duration', 20), data.get('difficulty', 'Medium'))
        return redirect(url_for('home'))
    settings = get_user_settings()
    return render_template('settings.html', settings=settings)

# Helpers for User Settings
def save_user_settings(sounds_enabled, timer_enabled, timer_duration, difficulty):
    session['sounds_enabled'] = sounds_enabled
    session['timer_enabled'] = timer_enabled
    session['timer_duration'] = timer_duration
    session['difficulty'] = difficulty

def get_user_settings():
    return {
        'sounds_enabled': session.get('sounds_enabled', True),
        'timer_enabled': session.get('timer_enabled', True),
        'timer_duration': session.get('timer_duration', 20),
        'difficulty': session.get('difficulty', 'Medium')
    }

# Error Handlers
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Run Application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)