import instaloader
from instagrapi import Client
from instagrapi.types import Media
import os
from datetime import datetime, timedelta

class Instagram:
    def __init__(self, username, password):
        """
        Initializes the Instagram clients.
        """
        self.L = instaloader.Instaloader()
        self.cl = Client()
        self.username = username
        self.password = password
        session_file = 'session.json'
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
                max_posts = 20
                cutoff_date = datetime.now() - timedelta(days=7)
                for post in profile.get_posts():
                    if count >= max_posts:
                        break
                    if post.is_video and post.date > cutoff_date:
                        all_reels.append(post)
                        count += 1
                print(f"Found {len(all_reels)} total reels so far.")
            except instaloader.ProfileNotExistsException:
                print(f"Profile @{username} does not exist.")
            except Exception as e:
                print(f"An error occurred while fetching from @{username}: {e}")
        return all_reels

    def download_reel(self, post):
        """
        Downloads a single reel.
        Returns the path to the video file.
        """
        try:
            print(f"Downloading reel from @{post.owner_username} (shortcode: {post.shortcode})...")
            self.L.download_post(post, target='temp_reels')
            video_path = None
            for f in os.listdir(f'temp_reels'):
                if f.endswith('.mp4'):
                    video_path = os.path.join('temp_reels', f)
                    break
            if video_path:
                print("Download complete.")
                return video_path
            else:
                print("Error: .mp4 file not found after download.")
                return None
        except Exception as e:
            print(f"Error downloading reel: {e}")
            return None

    def upload_reel(self, video_path, caption):
        """
        Uploads a reel to the logged-in account.
        """
        try:
            print("Uploading reel...")
            media = self.cl.video_upload(video_path, caption=caption)
            print("Upload successful!")
            return media
        except Exception as e:
            print(f"Error uploading reel: {e}")
            return None
