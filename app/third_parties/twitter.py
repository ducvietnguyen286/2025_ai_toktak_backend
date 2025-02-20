import os
import tweepy

X_MEDIA_ENDPOINT_URL = "https://api.x.com/2/media/upload"
X_POST_TO_X_URL = "https://api.x.com/2/tweets"


class TwitterService:
    def __init__(self, access_token, access_token_secret):
        self.consumer_key = os.environ.get("X_CONSUMER_KEY") or ""
        self.consumer_secret = os.environ.get("X_CONSUMER_SECRET") or ""

        self.access_token = access_token
        self.access_token_secret = access_token_secret

    def send_post(self, post, link):
        if post.type == "social":
            self.send_post_social(post, link)
        if post.type == "video":
            self.send_post_video(post, link)

    def send_post_social(self, post, link):
        pass

    def send_post_video(self, post, link):
        pass
