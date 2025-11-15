import os
import random
import shutil
import asyncio
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from instagram import Instagram

async def process_account(username, password, source_accounts, db_conn_str, db_name, max_posts, days_cutoff):
    """
    Asynchronously processes a single Instagram account.
    """
    logging.info(f"Processing account: {username}")

    # Account-specific collections
    mongo_collection_name = f"posted_reels_{username}"
    mongo_available_collection_name = f"available_reels_{username}"

    try:
        # Initialize Database and Instagram clients
        db = Database(db_conn_str, db_name, mongo_collection_name, mongo_available_collection_name)
        insta = Instagram(username, password)

        # Fetch all reels from source accounts
        all_reels = await insta.get_reels(source_accounts, max_posts, days_cutoff)

        if not all_reels:
            logging.warning("No reels found from the source accounts.")
            return

        # Save fetched reels to database
        db.add_available_reels(all_reels)

        # Get available reels not posted from database
        logging.info("Getting available reels not posted...")
        available_docs = db.get_available_not_posted()

        if not available_docs:
            logging.info("No new reels available to post.")
            return

        logging.info(f"Found {len(available_docs)} available reels to choose from.")

        # Select a random reel doc
        random_doc = random.choice(available_docs)
        shortcode = random_doc["shortcode"]

        # Fetch the post by shortcode
        random_reel = await insta.get_post_by_shortcode(shortcode)
        if not random_reel:
            logging.error("Failed to fetch the selected reel.")
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
            if await insta.upload_reel(video_path, caption, thumbnail_path):
                # Add to database if upload was successful
                db.add_posted_reel(random_reel.shortcode)
                logging.info(f"Successfully posted reel {random_reel.shortcode} and updated database.")
            else:
                logging.error(f"Failed to upload reel {random_reel.shortcode}.")

        # Clean up the temporary directory
        if os.path.exists('temp_reels'):
            shutil.rmtree('temp_reels')
            logging.info("Cleaned up temporary files.")

    except Exception as e:
        logging.error(f"An unexpected error occurred for account {username}: {e}")
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
    Function to schedule the main process.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', hours=24)  # Run daily
    scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
