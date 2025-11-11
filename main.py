import configparser
import random
import os
import shutil
from database import Database
from instagram import Instagram

def main():
    """
    Main function to run the Instagram automation script.
    """
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Instagram credentials
    insta_username = config['Instagram']['username']
    insta_password = config['Instagram']['password']
    source_accounts = [acc.strip() for acc in config['Instagram']['source_accounts'].split(',')]

    # MongoDB credentials
    mongo_conn_str = config['Mongo']['connection_string']
    mongo_db_name = config['Mongo']['database_name']
    mongo_collection_name = config['Mongo']['collection_name']
    mongo_available_collection_name = config['Mongo']['available_collection_name']

    # Check for placeholder credentials
    if 'YOUR_INSTAGRAM_USERNAME' in insta_username or 'YOUR_MONGODB_CONNECTION_STRING' in mongo_conn_str:
        print("Please update the config.ini file with your actual credentials.")
        return

    try:
        # Initialize Database and Instagram clients
        db = Database(mongo_conn_str, mongo_db_name, mongo_collection_name, mongo_available_collection_name)
        insta = Instagram(insta_username, insta_password)

        # Fetch all reels from source accounts
        all_reels = insta.get_reels(source_accounts)

        if not all_reels:
            print("No reels found from the source accounts.")
            return

        # Save fetched reels to database
        db.add_available_reels(all_reels)

        # Get available reels not posted from database
        print("Getting available reels not posted...")
        available_docs = db.get_available_not_posted()

        if not available_docs:
            print("No new reels available to post.")
            return

        print(f"Found {len(available_docs)} available reels to choose from.")

        # Select a random reel doc
        random_doc = random.choice(available_docs)
        shortcode = random_doc["shortcode"]

        # Fetch the post by shortcode
        random_reel = insta.get_post_by_shortcode(shortcode)
        if not random_reel:
            print("Failed to fetch the selected reel.")
            return
        
        # Create a temporary directory for downloads
        if not os.path.exists('temp_reels'):
            os.makedirs('temp_reels')

        # Download the reel
        video_path, thumbnail_path = insta.download_reel(random_reel)

        if video_path:
            # Create a caption
            caption = random_reel.caption

            # Upload the reel
            if insta.upload_reel(video_path, caption, thumbnail_path):
                # Add to database if upload was successful
                db.add_posted_reel(random_reel.shortcode)
                print(f"Successfully posted reel {random_reel.shortcode} and updated database.")
            else:
                print(f"Failed to upload reel {random_reel.shortcode}.")

        # Clean up the temporary directory
        if os.path.exists('temp_reels'):
            shutil.rmtree('temp_reels')
            print("Cleaned up temporary files.")

    except Exception as e:
        print(f"An unexpected error occurred in the main script: {e}")
        # Clean up just in case
        if os.path.exists('temp_reels'):
            shutil.rmtree('temp_reels')

if __name__ == "__main__":
    main()
