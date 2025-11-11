from pymongo import MongoClient

class Database:
    def __init__(self, connection_string, database_name, collection_name):
        """
        Initializes the database connection.
        """
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            # Test the connection
            self.client.server_info()
            print("Successfully connected to MongoDB.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
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
