import instaloader
from instagrapi import Client
from instagrapi.types import Media
import os
from datetime import datetime, timedelta
import time
import asyncio
import aiofiles
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

class Instagram:
    def __init__(self, username, password):
        """
        Initializes the Instagram clients.
        """
        self.username = username
        self.password = password
        self.L = instaloader.Instaloader(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.cl = Client()
        session_file = f'session_{self.username}.json'
        if os.path.exists(session_file):
            try:
                self.cl.load_settings(session_file)
                # Verify session is valid
                self.cl.user_info(self.username)
                print("Session loaded successfully.")
            except Exception as e:
                print(f"Session invalid ({e}), logging in...")
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(session_file)
                print("Login successful and session saved.")
        else:
            print("No session file found, logging in...")
            self.cl.login(self.username, self.password)
            self.cl.dump_settings(session_file)
            print("Login successful and session saved.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_reels(self, usernames, max_posts=10, days_cutoff=7):
        """
        Asynchronously fetches public reels from a list of usernames with retries and rate limiting.
        """
        all_reels = []
        cutoff_date = datetime.now() - timedelta(days=days_cutoff)
        for username in usernames:
            try:
                logging.info(f"Fetching reels from @{username}...")
                profile = instaloader.Profile.from_username(self.L.context, username)
                count = 0
                for post in profile.get_posts():
                    if count >= max_posts:
                        break
                    if post.is_video and post.date > cutoff_date:
                        all_reels.append(post)
                        count += 1
                    await asyncio.sleep(0.1)  # Small delay to avoid overwhelming
                logging.info(f"Found {len(all_reels)} total reels so far.")
                await asyncio.sleep(10)  # Delay to avoid rate limiting
            except instaloader.ProfileNotExistsException:
                logging.warning(f"Profile @{username} does not exist.")
            except Exception as e:
                logging.error(f"An error occurred while fetching from @{username}: {e}")
                await asyncio.sleep(10)  # Delay even on error
        return all_reels

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def download_reel(self, post):
        """
        Asynchronously downloads a single reel and its thumbnail with retries.
        Returns the paths to the video file and thumbnail.
        """
        try:
            logging.info(f"Downloading reel from @{post.owner_username} (shortcode: {post.shortcode})...")
            await asyncio.to_thread(self.L.download_post, post, target='temp_reels')
            video_path = None
            thumbnail_path = None
            for f in await asyncio.to_thread(os.listdir, 'temp_reels'):
                if f.endswith('.mp4'):
                    video_path = os.path.join('temp_reels', f)
                elif f.endswith('.jpg'):
                    thumbnail_path = os.path.join('temp_reels', f)
            if not video_path:
                logging.error("Error: .mp4 file not found after download.")
                return None, None
            logging.info("Download complete.")
            return video_path, thumbnail_path
        except Exception as e:
            logging.error(f"Error downloading reel: {e}")
            return None, None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_reel(self, video_path, caption, thumbnail_path=None):
        """
        Asynchronously uploads a reel to the logged-in account with retries.
        """
        try:
            logging.info("Uploading reel...")
            media = await asyncio.to_thread(self.cl.video_upload, video_path, caption=caption, thumbnail=thumbnail_path)
            logging.info("Upload successful!")
            return media
        except Exception as e:
            logging.error(f"Error uploading reel: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_post_by_shortcode(self, shortcode):
        """
        Asynchronously fetches a post by its shortcode with retries.
        """
        try:
            return await asyncio.to_thread(instaloader.Post.from_shortcode, self.L.context, shortcode)
        except Exception as e:
            logging.error(f"Error getting post {shortcode}: {e}")
            return None
