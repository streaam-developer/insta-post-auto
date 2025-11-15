from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import Database
import os
from dotenv import load_dotenv
from datetime import datetime
import openai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')  # Add to .env

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

mongo_conn_str = os.getenv('MONGO_CONNECTION_STRING')
mongo_db_name = os.getenv('MONGO_DATABASE_NAME')
openai.api_key = os.getenv('OPENAI_API_KEY')
db = Database(mongo_conn_str, mongo_db_name)

class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']
        self.role = user_doc['role']

@login_manager.user_loader
def load_user(user_id):
    user_doc = db.db.users.find_one({"_id": user_id})
    return User(user_doc) if user_doc else None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_doc = db.authenticate_user(username, password)
        if user_doc:
            user = User(user_doc)
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/accounts')
@login_required
def get_accounts():
    accounts = []
    i = 1
    while True:
        username = os.getenv(f'INSTA_USERNAME_{i}')
        if not username:
            break
        accounts.append(username)
        i += 1
    return jsonify(accounts)

@app.route('/api/reels/<username>')
@login_required
def get_reels(username):
    try:
        posted = db.get_posts(username)
        available = db.get_available_not_posted(username)
        return jsonify({'posted': posted, 'available': available})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/<username>')
@login_required
def get_analytics(username):
    try:
        posts = db.get_posts(username)
        total_views = sum(p.get('analytics', {}).get('views', 0) for p in posts)
        total_likes = sum(p.get('analytics', {}).get('likes', 0) for p in posts)
        total_shares = sum(p.get('analytics', {}).get('shares', 0) for p in posts)
        engagement_rate = (total_likes + total_shares) / max(total_views, 1) * 100 if total_views > 0 else 0
        return jsonify({
            'total_posts': len(posts),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_shares': total_shares,
            'engagement_rate': round(engagement_rate, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<username>')
@login_required
def get_logs(username):
    try:
        logs = db.get_logs(username, limit=50)
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/<username>', methods=['GET', 'POST'])
@login_required
def manage_queue(username):
    if request.method == 'GET':
        try:
            queue = db.get_queue(username)
            return jsonify(queue)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'POST':
        data = request.json
        shortcode = data.get('shortcode')
        scheduled_time = data.get('scheduled_time')
        if shortcode and scheduled_time:
            db.add_to_queue(username, shortcode, scheduled_time)
            return jsonify({'message': 'Added to queue'}), 201
        return jsonify({'error': 'Invalid data'}), 400

@app.route('/api/queue/<username>/<shortcode>', methods=['PUT', 'DELETE'])
@login_required
def update_queue(username, shortcode):
    if request.method == 'PUT':
        data = request.json
        status = data.get('status')
        if status:
            db.update_queue_status(shortcode, status)
            return jsonify({'message': 'Queue updated'})
        return jsonify({'error': 'Invalid status'}), 400
    elif request.method == 'DELETE':
        db.update_queue_status(shortcode, 'cancelled')
        return jsonify({'message': 'Queue item cancelled'})

@app.route('/api/alerts', methods=['GET', 'POST'])
@login_required
def manage_alerts():
    if request.method == 'GET':
        alerts = db.get_alerts(current_user.id)
        return jsonify(alerts)
    elif request.method == 'POST':
        data = request.json
        condition = data.get('condition')
        message = data.get('message')
        if condition and message:
            db.create_alert(current_user.id, condition, message)
            return jsonify({'message': 'Alert created'}), 201
        return jsonify({'error': 'Invalid data'}), 400

@app.route('/api/ai-suggest', methods=['POST'])
@login_required
def ai_suggest():
    data = request.json
    prompt = data.get('prompt', 'Suggest a caption for an Instagram reel')
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100
        )
        suggestion = response.choices[0].text.strip()
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
