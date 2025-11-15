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

async def check_and_post():
    """
    Check each account and post if 5 hours have passed since last post.
    """
    load_dotenv()

    # Load environment variables
    mongo_conn_str = os.getenv('MONGO_CONNECTION_STRING')
    mongo_db_name = os.getenv('MONGO_DATABASE_NAME')
    max_posts = int(os.getenv('MAX_POSTS_PER_ACCOUNT', 10))
    days_cutoff = int(os.getenv('DAYS_CUTOFF', 7))
    db = Database(mongo_conn_str, mongo_db_name)

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

    from datetime import datetime, timedelta

    # Check each account
    for username, password, source_accounts in accounts:
        last_post_time = db.get_last_post_time(username)
        if last_post_time is None or (datetime.utcnow() - last_post_time) >= timedelta(hours=5):
            logging.info(f"Posting for account {username}")
            await process_account(username, password, source_accounts, mongo_conn_str, mongo_db_name, max_posts, days_cutoff)
            db.update_last_post_time(username, datetime.utcnow())
        else:
            logging.info(f"Account {username} not ready to post yet")

def schedule_posts():
    """
    Function to schedule the check_and_post process every 30 minutes.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_post, 'interval', minutes=30)  # Check every 30 minutes
    scheduler.start()

def run_flask():
    """
    Run the Flask app in a separate thread.
    """
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

async def main_entry():
    """
    Main entry point to run initial check and start scheduler.
    """
    # Run initial check
    await check_and_post()

    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_post, 'interval', minutes=30)
    scheduler.start()

    # Keep the event loop running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down scheduler...")
        scheduler.shutdown()
        logging.info("Scheduler shut down.")

if __name__ == "__main__":
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run the async main entry
    try:
        asyncio.run(main_entry())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")
