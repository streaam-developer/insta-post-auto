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

    # Check for placeholder credentials
    if 'YOUR_INSTAGRAM_USERNAME' in insta_username or 'YOUR_MONGODB_CONNECTION_STRING' in mongo_conn_str:
        print("Please update the config.ini file with your actual credentials.")
        return

    try:
        # Initialize Database and Instagram clients
        db = Database(mongo_conn_str, mongo_db_name, mongo_collection_name)
        insta = Instagram(insta_username, insta_password)

        # Fetch all reels from source accounts
        all_reels = insta.get_reels(source_accounts)

        if not all_reels:
            print("No reels found from the source accounts.")
            return

        # Filter out already posted reels
        print("Filtering out already posted reels...")
        new_reels = [reel for reel in all_reels if not db.check_if_posted(reel.shortcode)]

        if not new_reels:
            print("No new reels to post. Everything is up to date.")
            return

        print(f"Found {len(new_reels)} new reels to choose from.")

        # Select a random reel
        random_reel = random.choice(new_reels)
        
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
