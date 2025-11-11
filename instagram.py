import instaloader
from instagrapi import Client
from instagrapi.types import Media
import os
from datetime import datetime, timedelta
import time

class Instagram:
    def __init__(self, username, password, proxy=None):
        """
        Initializes the Instagram clients.
        """
        self.username = username
        self.password = password
        self.proxy = proxy
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        self.L = instaloader.Instaloader(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', proxies=proxies)
        self.cl = Client(proxy=proxy)
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

    def get_reels(self, usernames):
        """
        Fetches public reels from a list of usernames.
        """
        all_reels = []
        for username in usernames:
            try:
                print(f"Fetching reels from @{username}...")
                profile = instaloader.Profile.from_username(self.L.context, username)
                count = 0
                max_posts = 10
                cutoff_date = datetime.now() - timedelta(days=7)
                for post in profile.get_posts():
                    if count >= max_posts:
                        break
                    if post.is_video and post.date > cutoff_date:
                        all_reels.append(post)
                        count += 1
                print(f"Found {len(all_reels)} total reels so far.")
                time.sleep(10)  # Delay to avoid rate limiting
            except instaloader.ProfileNotExistsException:
                print(f"Profile @{username} does not exist.")
            except Exception as e:
                print(f"An error occurred while fetching from @{username}: {e}")
                time.sleep(10)  # Delay even on error
        return all_reels

    def download_reel(self, post):
        """
        Downloads a single reel and its thumbnail.
        Returns the paths to the video file and thumbnail.
        """
        try:
            print(f"Downloading reel from @{post.owner_username} (shortcode: {post.shortcode})...")
            self.L.download_post(post, target='temp_reels')
            video_path = None
            thumbnail_path = None
            for f in os.listdir('temp_reels'):
                if f.endswith('.mp4'):
                    video_path = os.path.join('temp_reels', f)
                elif f.endswith('.jpg'):
                    thumbnail_path = os.path.join('temp_reels', f)
            if not video_path:
                print("Error: .mp4 file not found after download.")
                return None, None
            print("Download complete.")
            return video_path, thumbnail_path
        except Exception as e:
            print(f"Error downloading reel: {e}")
            return None, None

    def upload_reel(self, video_path, caption, thumbnail_path=None):
        """
        Uploads a reel to the logged-in account.
        """
        try:
            print("Uploading reel...")
            media = self.cl.video_upload(video_path, caption=caption, thumbnail=thumbnail_path)
            print("Upload successful!")
            return media
        except Exception as e:
            print(f"Error uploading reel: {e}")
            return None

    def get_post_by_shortcode(self, shortcode):
        """
        Fetches a post by its shortcode.
        """
        try:
            return instaloader.Post.from_shortcode(self.L.context, shortcode)
        except Exception as e:
            print(f"Error getting post {shortcode}: {e}")
            return None
