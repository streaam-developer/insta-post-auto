from flask import Flask, render_template, jsonify
from database import Database
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

mongo_conn_str = os.getenv('MONGO_CONNECTION_STRING')
mongo_db_name = os.getenv('MONGO_DATABASE_NAME')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/accounts')
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
def get_reels(username):
    try:
        db = Database(mongo_conn_str, mongo_db_name, f"posted_reels_{username}", f"available_reels_{username}")
        posted = list(db.collection.find({}, {'_id': 0}))
        available = list(db.available_collection.find({}, {'_id': 0}))
        return jsonify({'posted': posted, 'available': available})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
