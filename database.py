from pymongo import MongoClient
import logging

class Database:
    def __init__(self, connection_string, database_name, collection_name, available_collection_name):
        """
        Initializes the database connection.
        """
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            self.available_collection = self.db[available_collection_name]
            # Test the connection
            self.client.server_info()
            logging.info("Successfully connected to MongoDB.")
        except Exception as e:
            logging.error(f"Error connecting to MongoDB: {e}")
            raise

    def check_if_posted(self, reel_shortcode):
        """
        Checks if a reel's shortcode already exists in the database.
        """
        return self.collection.find_one({"shortcode": reel_shortcode}) is not None

    def add_posted_reel(self, reel_shortcode):
        """
        Adds a reel's shortcode to the database.
        """
        self.collection.insert_one({"shortcode": reel_shortcode})

    def add_available_reels(self, posts):
        """
        Adds fetched reels to the available collection.
        """
        docs = [{"shortcode": p.shortcode, "owner_username": p.owner_username, "caption": p.caption, "date": p.date} for p in posts]
        try:
            self.available_collection.insert_many(docs, ordered=False)
            logging.info(f"Added {len(docs)} reels to available collection.")
        except Exception as e:
            logging.error(f"Error adding available reels: {e}")

    def get_available_not_posted(self):
        """
        Gets available reels that haven't been posted yet.
        """
        posted_shortcodes = [doc["shortcode"] for doc in self.collection.find({}, {"shortcode": 1, "_id": 0})]
        return list(self.available_collection.find({"shortcode": {"$nin": posted_shortcodes}}))
