import os
import random
import shutil
import asyncio
import logging
import threading
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from instagram import Instagram
from app import app

async def process_account(username, password, source_accounts, db_conn_str, db_name, max_posts, days_cutoff):
    """
    Asynchronously processes a single Instagram account.
    """
    db = Database(db_conn_str, db_name)
    db.log_activity("INFO", f"Processing account: {username}", username, "process_start")

    try:
        # Initialize Instagram client
        insta = Instagram(username, password)

        # Fetch all reels from source accounts
        all_reels = await insta.get_reels(source_accounts, max_posts, days_cutoff)

        if not all_reels:
            db.log_activity("WARNING", "No reels found from the source accounts.", username, "fetch_reels")
            return

        # Save fetched reels to database
        db.add_available_reels(username, all_reels)

        # Get available reels not posted from database
        db.log_activity("INFO", "Getting available reels not posted...", username, "get_available")
        available_docs = db.get_available_not_posted(username)

        if not available_docs:
            db.log_activity("INFO", "No new reels available to post.", username, "no_available")
            return

        db.log_activity("INFO", f"Found {len(available_docs)} available reels to choose from.", username, "available_count")

        # Select a random reel doc
        random_doc = random.choice(available_docs)
        shortcode = random_doc["shortcode"]

        # Fetch the post by shortcode
        random_reel = await insta.get_post_by_shortcode(shortcode)
        if not random_reel:
            db.log_activity("ERROR", "Failed to fetch the selected reel.", username, "fetch_reel")
            return

        # Create a temporary directory for downloads
        if not os.path.exists('temp_reels'):
            os.makedirs('temp_reels')

        # Download the reel
        video_path, thumbnail_path = await insta.download_reel(random_reel)

        if video_path:
            # Create a caption
            caption = random_reel.caption

            # Upload the reel
            upload_result = await insta.upload_reel(video_path, caption, thumbnail_path)
            if upload_result:
                # Add to database if upload was successful
                db.add_posted_reel(username, random_reel)
                db.log_activity("INFO", f"Successfully posted reel {random_reel.shortcode}", username, "post_success")
                # Fetch analytics after posting
                analytics = await insta.get_reel_analytics(upload_result.id)
                if analytics:
                    db.update_post_analytics(random_reel.shortcode, analytics)
            else:
                db.log_activity("ERROR", f"Failed to upload reel {random_reel.shortcode}", username, "post_failure")

        # Clean up the temporary directory
        if os.path.exists('temp_reels'):
            shutil.rmtree('temp_reels')
            db.log_activity("INFO", "Cleaned up temporary files.", username, "cleanup")

    except Exception as e:
        db.log_activity("ERROR", f"An unexpected error occurred: {e}", username, "error")
        # Clean up just in case
        if os.path.exists('temp_reels'):
            shutil.rmtree('temp_reels')

async def main():
    """
    Main async function to run the Instagram automation script.
    """
    load_dotenv()

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load environment variables
    mongo_conn_str = os.getenv('MONGO_CONNECTION_STRING')
    mongo_db_name = os.getenv('MONGO_DATABASE_NAME')
    max_posts = int(os.getenv('MAX_POSTS_PER_ACCOUNT', 10))
    days_cutoff = int(os.getenv('DAYS_CUTOFF', 7))

    # Load accounts from env
    accounts = []
    i = 1
    while True:
        username = os.getenv(f'INSTA_USERNAME_{i}')
        password = os.getenv(f'INSTA_PASSWORD_{i}')
        source_accounts = os.getenv(f'INSTA_SOURCE_ACCOUNTS_{i}')
        if not username or not password or not source_accounts:
            break
        source_accounts = [acc.strip() for acc in source_accounts.split(',')]
        accounts.append((username, password, source_accounts))
        i += 1

    if not accounts:
        logging.error("No Instagram accounts configured in .env")
        return

    # Process accounts concurrently
    tasks = [process_account(username, password, source_accounts, mongo_conn_str, mongo_db_name, max_posts, days_cutoff) for username, password, source_accounts in accounts]
    await asyncio.gather(*tasks)

def schedule_posts():
    """
    Function to schedule the main process every 5 hours.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', hours=5)  # Run every 5 hours
    scheduler.start()

def run_flask():
    """
    Run the Flask app in a separate thread.
    """
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == "__main__":
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run initial process and start scheduler
    asyncio.run(main())
    schedule_posts()
