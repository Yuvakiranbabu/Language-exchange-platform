from flask import Flask, request, render_template_string, redirect, url_for, render_template, session
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import logging
import socket

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('chat_app')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Add a secret key for session management
socketio = SocketIO(app, cors_allowed_origins="*", logger=logger, engineio_logger=True)

# Check if port 5004 is in use
def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

if check_port(5004):
    logger.warning('Port 5004 is already in use. Consider changing the port.')

# Set up SQLite database
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT,
                password TEXT,
                nativeLanguage TEXT,
                targetLanguage TEXT,
                last_partner TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                partner_email TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email),
                FOREIGN KEY (partner_email) REFERENCES users(email)
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return render_template_string('''
        <div><a href="/">Home</a></div>
        <h1>Welcome to Language Exchange Platform</h1>
        <p>Connect with people to practice languages!</p>
        <a href="/signup">Sign Up</a> | <a href="/login">Login</a>
        <style>
            body { font-family: Arial; margin: 20px; }
            div { margin-bottom: 10px; }
            a { color: #007bff; text-decoration: none; margin-right: 10px; }
            a:hover { text-decoration: underline; }
        </style>
    ''')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        native = request.form['nativeLanguage']
        target = request.form['targetLanguage']
        with sqlite3.connect('users.db') as conn:
            try:
                conn.execute('INSERT INTO users (email, name, password, nativeLanguage, targetLanguage, last_partner) VALUES (?, ?, ?, ?, ?, ?)',
                            (email, name, password, native, target, None))
                conn.commit()
                return render_template_string('''
                    <div><a href="/">Home</a></div>
                    <p>Account created! <a href="/login">Login now</a></p>
                    <style>
                        body { font-family: Arial; margin: 20px; }
                        div { margin-bottom: 10px; }
                        a { color: #007bff; text-decoration: none; margin-right: 10px; }
                        a:hover { text-decoration: underline; }
                    </style>
                ''')
            except sqlite3.IntegrityError:
                return render_template_string('''
                    <div><a href="/">Home</a></div>
                    <p>Email already exists! <a href="/signup">Try again</a></p>
                    <style>
                        body { font-family: Arial; margin: 20px; }
                        div { margin-bottom: 10px; }
                        a { color: #007bff; text-decoration: none; margin-right: 10px; }
                        a:hover { text-decoration: underline; }
                    </style>
                ''')
    return render_template_string('''
        <div><a href="/">Home</a></div>
        <h1>Sign Up</h1>
        <form method="POST">
            <label>Email: <input type="email" name="email" required></label><br>
            <label>Name: <input type="text" name="name" placeholder="e.g., Maria" required></label><br>
            <label>Password: <input type="password" name="password" required></label><br>
            <label>Native Language: <input type="text" name="nativeLanguage" placeholder="e.g., English" required></label><br>
            <label>Target Language: <input type="text" name="targetLanguage" placeholder="e.g., Spanish" required></label><br>
            <button type="submit">Create Account</button>
        </form>
        <style>
            body { font-family: Arial; margin: 20px; }
            div { margin-bottom: 10px; }
            form { display: flex; flex-direction: column; gap: 10px; max-width: 300px; }
            label { display: flex; flex-direction: column; }
            input { padding: 8px; }
            button { padding: 10px; background: #007bff; color: white; border: none; }
            button:hover { background: #0056b3; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('users.db') as conn:
            cursor = conn.execute('SELECT password FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            if user and user[0] == password:
                session['email'] = email  # Store email in session
                return redirect(url_for('dashboard', email=email))
            else:
                return render_template_string('''
                    <div><a href="/">Home</a></div>
                    <p>Wrong email or password! <a href="/login">Try again</a></p>
                    <style>
                        body { font-family: Arial; margin: 20px; }
                        div { margin-bottom: 10px; }
                        a { color: #007bff; text-decoration: none; margin-right: 10px; }
                        a:hover { text-decoration: underline; }
                    </style>
                ''')
    return render_template_string('''
        <div><a href="/">Home</a></div>
        <h1>Login</h1>
        <form method="POST">
            <label>Email: <input type="email" name="email" required></label><br>
            <label>Password: <input type="password" name="password" required></label><br>
            <button type="submit">Login</button>
        </form>
        <style>
            body { font-family: Arial; margin: 20px; }
            div { margin-bottom: 10px; }
            form { display: flex; flex-direction: column; gap: 10px; max-width: 300px; }
            label { display: flex; flex-direction: column; }
            input { padding: 8px; }
            button { padding: 10px; background: #007bff; color: white; border: none; }
            button:hover { background: #0056b3; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    ''')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        target_language = request.form['targetLanguage']
        email = request.form['email']
        with sqlite3.connect('users.db') as conn:
            cursor = conn.execute('SELECT email, name, nativeLanguage, targetLanguage FROM users WHERE nativeLanguage = ? AND email != ?',
                                (target_language, email))
            matches = cursor.fetchall()
            matches_html = ''.join([f'<li><a href="{url_for("chat", user_email=email, partner_email=m[0])}">{m[1]} ({m[0]})</a> - Speaks: {m[2]}, Wants: {m[3]}</li>' for m in matches]) or '<li>No matches found!</li>'
            return redirect(url_for('dashboard', email=email, matches_html=matches_html))
    return render_template_string('''
        <div><a href="/">Home</a></div>
        <h1>Search for Partners</h1>
        <form method="POST">
            <input type="hidden" name="email" value="{{ email }}">
            <label>Target Language: <input type="text" name="targetLanguage" placeholder="e.g., Spanish" required></label><br>
            <button type="submit">Search</button>
        </form>
        <style>
            body { font-family: Arial; margin: 20px; }
            div { margin-bottom: 10px; }
            form { display: flex; flex-direction: column; gap: 10px; max-width: 300px; }
            label { display: flex; flex-direction: column; }
            input { padding: 8px; }
            button { padding: 10px; background: #007bff; color: white; border: none; }
            button:hover { background: #0056b3; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    ''', email=request.args.get('email', ''))

@app.route('/dashboard')
def dashboard():
    email = request.args.get('email', session.get('email'))
    matches_html = request.args.get('matches_html', '<li>No matches yet!</li>')
    if not email:
        return render_template_string('''
            <div><a href="/">Home</a></div>
            <p>Please login first! <a href="/login">Login</a></p>
            <style>
                body { font-family: Arial; margin: 20px; }
                div { margin-bottom: 10px; }
                a { color: #007bff; text-decoration: none; margin-right: 10px; }
                a:hover { text-decoration: underline; }
            </style>
        ''')
    with sqlite3.connect('users.db') as conn:
        cursor = conn.execute('SELECT email, name, nativeLanguage, targetLanguage, last_partner FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        if not user:
            return render_template_string('''
                <div><a href="/">Home</a></div>
                <p>User not found! <a href="/login">Login again</a></p>
                <style>
                    body { font-family: Arial; margin: 20px; }
                    div { margin-bottom: 10px; }
                    a { color: #007bff; text-decoration: none; margin-right: 10px; }
                    a:hover { text-decoration: underline; }
                </style>
            ''')
        last_partner_email = user[4] if user[4] else 'No recent partner'
        last_partner_name = conn.execute('SELECT name FROM users WHERE email = ?', (user[4],)).fetchone()
        last_partner_name = last_partner_name[0] if last_partner_name else 'Unknown'
        return render_template_string('''
            <div><a href="/">Home</a></div>
            <h1>Your Dashboard</h1>
            <p><strong>Name:</strong> {{ name }}</p>
            <p><strong>Email:</strong> {{ email }}</p>
            <p><strong>Native Language:</strong> {{ native }}</p>
            <p><strong>Target Language:</strong> {{ target }}</p>
            <p><strong>Last Chatted Partner:</strong> <a href="{{ url_for('chat', user_email=email, partner_email=last_partner_email) if last_partner_email != 'No recent partner' else '#' }}">{{ last_partner_name }}</a></p>
            <h2>Your Matches</h2>
            <ul>{{ matches_html | safe }}</ul>
            <a href="{{ url_for('search', email=email) }}">Search for Partners</a>
            <style>
                body { font-family: Arial; margin: 20px; }
                div { margin-bottom: 10px; }
                p { margin: 10px 0; }
                ul { margin: 10px 0; padding-left: 20px; }
                a { color: #007bff; text-decoration: none; margin-right: 10px; }
                a:hover { text-decoration: underline; }
            </style>
        ''', email=user[0], name=user[1], native=user[2], target=user[3], last_partner_email=last_partner_email, last_partner_name=last_partner_name, matches_html=matches_html)

@app.route('/chat/<user_email>/<partner_email>')
def chat(user_email, partner_email):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.execute('SELECT name FROM users WHERE email = ?', (partner_email,))
        partner = cursor.fetchone()
        if not partner:
            return render_template_string('''
                <div><a href="/">Home</a></div>
                <p>Partner not found! <a href="/dashboard?email={{ email }}">Back to Dashboard</a></p>
                <style>
                    body { font-family: Arial; margin: 20px; }
                    div { margin-bottom: 10px; }
                    a { color: #007bff; text-decoration: none; margin-right: 10px; }
                    a:hover { text-decoration: underline; }
                </style>
            ''', email=user_email)
        # Update last_partner for the user
        conn.execute('UPDATE users SET last_partner = ? WHERE email = ?', (partner_email, user_email))
        conn.commit()
        # Fetch existing messages
        cursor = conn.execute('SELECT user_email, message, timestamp FROM messages WHERE (user_email = ? AND partner_email = ?) OR (user_email = ? AND partner_email = ?) ORDER BY timestamp',
                            (user_email, partner_email, partner_email, user_email))
        messages = cursor.fetchall()
    return render_template('chat.html', user_email=user_email, partner_email=partner_email, partner_name=partner[0], messages=messages)

@socketio.on('join')
def on_join(data):
    user = data['user']
    partner = data['partner']
    room = ':'.join(sorted([user, partner]))
    join_room(room)
    logger.debug(f'User {user} joined room {room}')
    emit('message', {'user': 'System', 'message': f'{user} joined the chat'}, room=room)

@socketio.on('message')
def on_message(data):
    user = data['user']
    partner = data['partner']
    message = data['message']
    room = ':'.join(sorted([user, partner]))
    logger.debug(f'Message from {user} to {partner} in room {room}: {message}')
    emit('message', {'user': user, 'message': message}, room=room)
    # Save message to database
    with sqlite3.connect('users.db') as conn:
        conn.execute('INSERT INTO messages (user_email, partner_email, message) VALUES (?, ?, ?)',
                    (user, partner, message))
        conn.commit()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5004)