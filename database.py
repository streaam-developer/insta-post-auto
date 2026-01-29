from pymongo import MongoClient
import logging
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, connection_string, database_name):
        """
        Initializes the database connection.
        """
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            # Test the connection
            self.client.server_info()
            logging.info("Successfully connected to MongoDB.")
        except Exception as e:
            logging.error(f"Error connecting to MongoDB: {e}")
            raise

    # User management
    def create_user(self, username, password, role='editor'):
        """
        Creates a new user with hashed password.
        """
        hashed_password = generate_password_hash(password)
        user_doc = {
            "username": username,
            "password": hashed_password,
            "role": role,
            "created_at": datetime.utcnow()
        }
        self.db.users.insert_one(user_doc)
        logging.info(f"User {username} created.")

    def authenticate_user(self, username, password):
        """
        Authenticates a user.
        """
        user = self.db.users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            return user
        return None

    # Posts and analytics
    def add_posted_reel(self, account_username, reel_data, analytics=None):
        """
        Adds a posted reel with analytics.
        """
        doc = {
            "account_username": account_username,
            "shortcode": reel_data.shortcode,
            "caption": reel_data.caption,
            "post_date": datetime.utcnow(),
            "owner_username": reel_data.owner_username,
            "analytics": analytics or {}
        }
        self.db.posts.insert_one(doc)
        logging.info(f"Posted reel {reel_data.shortcode} added to database.")

    def update_post_analytics(self, shortcode, analytics):
        """
        Updates analytics for a post.
        """
        self.db.posts.update_one(
            {"shortcode": shortcode},
            {"$set": {"analytics": analytics, "last_updated": datetime.utcnow()}}
        )

    def get_posts(self, account_username=None):
        """
        Gets posts, optionally filtered by account.
        """
        query = {}
        if account_username:
            query["account_username"] = account_username
        return list(self.db.posts.find(query, {"_id": 0}))

    # Available reels
    def add_available_reels(self, account_username, posts):
        """
        Adds fetched reels to the available collection for an account.
        """
        docs = [{
            "account_username": account_username,
            "shortcode": p.shortcode,
            "owner_username": p.owner_username,
            "caption": p.caption,
            "date": p.date
        } for p in posts]
        try:
            self.db.available_reels.insert_many(docs, ordered=False)
            logging.info(f"Added {len(docs)} reels to available collection for {account_username}.")
        except Exception as e:
            logging.error(f"Error adding available reels: {e}")

    def get_available_not_posted(self, account_username):
        """
        Gets available reels that haven't been posted yet for an account.
        """
        posted_shortcodes = [doc["shortcode"] for doc in self.db.posts.find({"account_username": account_username}, {"shortcode": 1, "_id": 0})]
        return list(self.db.available_reels.find({
            "account_username": account_username,
            "shortcode": {"$nin": posted_shortcodes}
        }))

    # Queue management
    def add_to_queue(self, account_username, shortcode, scheduled_time):
        """
        Adds a reel to the posting queue.
        """
        doc = {
            "account_username": account_username,
            "shortcode": shortcode,
            "scheduled_time": scheduled_time,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        self.db.queue.insert_one(doc)

    def get_queue(self, account_username=None):
        """
        Gets the queue, optionally filtered by account.
        """
        query = {}
        if account_username:
            query["account_username"] = account_username
        return list(self.db.queue.find(query, {"_id": 0}))

    def update_queue_status(self, shortcode, status):
        """
        Updates the status of a queued item.
        """
        self.db.queue.update_one(
            {"shortcode": shortcode},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

    # Logging
    def log_activity(self, level, message, account_username=None, action_type=None):
        """
        Logs an activity.
        """
        doc = {
            "timestamp": datetime.utcnow(),
            "level": level,
            "message": message,
            "account_username": account_username,
            "action_type": action_type
        }
        self.db.logs.insert_one(doc)

    def get_logs(self, account_username=None, limit=100):
        """
        Gets logs, optionally filtered by account.
        """
        query = {}
        if account_username:
            query["account_username"] = account_username
        return list(self.db.logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit))

    # Alerts
    def create_alert(self, user_id, condition, message, enabled=True):
        """
        Creates a custom alert.
        """
        doc = {
            "user_id": user_id,
            "condition": condition,
            "message": message,
            "enabled": enabled,
            "created_at": datetime.utcnow()
        }
        self.db.alerts.insert_one(doc)

    def get_alerts(self, user_id):
        """
        Gets alerts for a user.
        """
        return list(self.db.alerts.find({"user_id": user_id, "enabled": True}, {"_id": 0}))

    # Account status
    def get_last_post_time(self, account_username):
        """
        Gets the last post time for an account.
        """
        status = self.db.account_status.find_one({"account_username": account_username})
        return status.get("last_post_time") if status else None

    def update_last_post_time(self, account_username, time):
        """
        Updates the last post time for an account.
        """
        self.db.account_status.update_one(
            {"account_username": account_username},
            {"$set": {"last_post_time": time}},
            upsert=True
        )
