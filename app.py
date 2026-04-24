from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)
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
    conn = sqlite3.connect('algoarena.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            status TEXT NOT NULL,
            date_solved TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db()
    
    topic_filter = request.args.get('topic', 'All')
    difficulty_filter = request.args.get('difficulty', 'All')
    status_filter = request.args.get('status', 'All')
    
    all_problems = conn.execute('SELECT * FROM problems ORDER BY date_solved DESC').fetchall()
    
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
def add():
    if request.method == 'POST':
        conn = get_db()
        conn.execute(
            'INSERT INTO problems (name, topic, difficulty, status, date_solved) VALUES (?, ?, ?, ?, ?)',
            (request.form['name'], request.form['topic'], request.form['difficulty'], request.form['status'], str(date.today()))
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
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
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM problems WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))
if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)