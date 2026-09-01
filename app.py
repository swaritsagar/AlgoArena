from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3
from datetime import date
from google import genai
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = 'algoarena_secret_key_2024'

def calculate_streak(problems):
    if not problems:
        return 0
    
    dates = sorted(set(p['date_solved'] for p in problems), reverse=True)
    
    streak = 1
    for i in range(1, len(dates)):
        d1 = date.fromisoformat(dates[i-1])
        d2 = date.fromisoformat(dates[i])
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break
    
    today = str(date.today())
    if dates[0] != today:
        return 0
    
    return streak
def get_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'algoarena.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            status TEXT NOT NULL,
            date_solved TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            conn.close()
            return render_template('register.html', error='Username already taken!')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid username or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db()
    
    topic_filter = request.args.get('topic', 'All')
    difficulty_filter = request.args.get('difficulty', 'All')
    status_filter = request.args.get('status', 'All')
    
    all_problems = conn.execute('SELECT * FROM problems WHERE user_id = ? ORDER BY date_solved DESC', (session['user_id'],)).fetchall()
    
    filtered = [p for p in all_problems
                if (topic_filter == 'All' or p['topic'] == topic_filter)
                and (difficulty_filter == 'All' or p['difficulty'] == difficulty_filter)
                and (status_filter == 'All' or p['status'] == status_filter)]
    
    total = len(all_problems)
    solved = len([p for p in all_problems if p['status'] == 'Solved'])
    
    topic_stats = {}
    for p in all_problems:
        t = p['topic']
        if t not in topic_stats:
            topic_stats[t] = {'solved': 0, 'total': 0}
        topic_stats[t]['total'] += 1
        if p['status'] == 'Solved':
            topic_stats[t]['solved'] += 1
    
    streak = calculate_streak(all_problems)
    weak_topics = [topic for topic, stats in topic_stats.items() if stats['total'] > 0 and (stats['solved'] / stats['total']) < 0.5]
    
    topics = sorted(set(p['topic'] for p in all_problems))
    
    conn.close()
    return render_template('index.html',
        problems=filtered,
        total=total,
        solved=solved,
        topic_stats=topic_stats,
        streak=streak,
        weak_topics=weak_topics,
        topics=topics,
        topic_filter=topic_filter,
        difficulty_filter=difficulty_filter,
        status_filter=status_filter)
    conn = get_db()
    problems = conn.execute('SELECT * FROM problems ORDER BY date_solved DESC').fetchall()
    
    total = len(problems)
    solved = len([p for p in problems if p['status'] == 'Solved'])
    
    topic_stats = {}
    for p in problems:
        t = p['topic']
        if t not in topic_stats:
            topic_stats[t] = {'solved': 0, 'total': 0}
        topic_stats[t]['total'] += 1
        if p['status'] == 'Solved':
            topic_stats[t]['solved'] += 1
    
    conn.close()
    streak = calculate_streak(problems)
    weak_topics = [topic for topic, stats in topic_stats.items() if stats['total'] > 0 and (stats['solved'] / stats['total']) < 0.5]
    return render_template('index.html', problems=problems, total=total, solved=solved, topic_stats=topic_stats, streak=streak, weak_topics=weak_topics)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        conn = get_db()
        conn.execute(
            'INSERT INTO problems (user_id, name, topic, difficulty, status, date_solved) VALUES (?, ?, ?, ?, ?, ?)',
            (session['user_id'], request.form['name'], request.form['topic'], request.form['difficulty'], request.form['status'], str(date.today()))
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute(
            'UPDATE problems SET name=?, topic=?, difficulty=?, status=? WHERE id=?',
            (request.form['name'], request.form['topic'], request.form['difficulty'], request.form['status'], id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit.html', problem=problem)
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM problems WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))
@app.route('/study-plan')
@login_required
def study_plan():
    conn = get_db()
    problems = conn.execute('SELECT * FROM problems').fetchall()
    conn.close()
    
    topic_stats = {}
    for p in problems:
        t = p['topic']
        if t not in topic_stats:
            topic_stats[t] = {'solved': 0, 'total': 0}
        topic_stats[t]['total'] += 1
        if p['status'] == 'Solved':
            topic_stats[t]['solved'] += 1
    
    weak_topics = [topic for topic, stats in topic_stats.items() 
                   if stats['total'] > 0 and (stats['solved'] / stats['total']) < 0.5]
    
    if not weak_topics:
        plan = "Great job! You have no weak topics right now. Keep practicing to maintain your strength!"
    else:
        prompt = f"""You are a DSA expert and coding interview coach.
        A student is preparing for software engineering interviews.
        Their weak DSA topics are: {', '.join(weak_topics)}
        
        Create a focused 7-day study plan to improve these weak areas.
        For each day specify:
        - Which topic to focus on
        - 3 specific problems to solve (Easy/Medium/Hard mix)
        - One key concept to master
        
        Keep it practical, specific and motivating.
        Format it clearly day by day."""
        
        response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        plan = response.text
    
    return render_template('study_plan.html', plan=plan, weak_topics=weak_topics)

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    data = request.get_json()
    question = data.get('question', '')
    
    prompt = f"""You are a DSA expert helping a student prepare for coding interviews.
    Answer this question clearly and concisely with examples where helpful.
    Focus on practical understanding, not just theory.
    
    Question: {question}"""
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return jsonify({'answer': response.text})
if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)