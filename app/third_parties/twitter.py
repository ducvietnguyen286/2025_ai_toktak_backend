import time

import requests

X_MEDIA_ENDPOINT_URL = "https://api.x.com/2/media/upload"
X_POST_TO_X_URL = "https://api.x.com/2/tweets"


class TwitterService:
    def __init__(self, access_token):
        self.access_token = access_token
        self.total_bytes = 0
        self.media_id = None
        self.processing_info = None
        self.headers = {
            "Authorization": "Bearer {}".format(self.access_token),
            "Content-Type": "application/json",
            "User-Agent": "MediaUploadSampleCode",
        }

    def upload_init(self, post):
        response = requests.head(post.video_url)
        self.total_bytes = int(response.headers.get("Content-Length", 0))

        request_data = {
            "command": "INIT",
            "media_type": "video/mp4",
            "total_bytes": self.total_bytes,
            "media_category": "tweet_video",
        }

        req = requests.post(
            url=X_MEDIA_ENDPOINT_URL, params=request_data, headers=self.headers
        )
        media_id = req.json()["data"]["id"]
        self.media_id = media_id

    def upload_append(self, post):
        segment_id = 0
        bytes_sent = 0

        response = requests.get(post.video_url, stream=True)
        response.raise_for_status()

        for chunk in response.iter_content(
            chunk_size=4 * 1024 * 1024
        ):  # 4MB chunk size
            files = {"media": ("chunk", chunk, "application/octet-stream")}

            data = {
                "command": "APPEND",
                "media_id": self.media_id,
                "segment_index": segment_id,
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": "MediaUploadSampleCode",
            }

            req = requests.post(
                url=X_MEDIA_ENDPOINT_URL, data=data, files=files, headers=headers
            )

            if req.status_code < 200 or req.status_code > 299:
                raise Exception(req.text)

            segment_id += 1
            bytes_sent += len(chunk)

            print(f"{bytes_sent} of {self.total_bytes} bytes uploaded")

        print("Upload chunks complete.")

    def upload_finalize(self):

        print("FINALIZE")

        request_data = {"command": "FINALIZE", "media_id": self.media_id}

        req = requests.post(
            url=X_MEDIA_ENDPOINT_URL, params=request_data, headers=self.headers
        )

        self.processing_info = req.json()["data"].get("processing_info", None)
        self.check_status()

    def check_status(self):
        if self.processing_info is None:
            return

        state = self.processing_info["state"]

        print("Media processing status is %s " % state)

        if state == "succeeded":
            return

        if state == "failed":
            raise Exception("Upload failed")

        check_after_secs = self.processing_info["check_after_secs"]

        print("Checking after %s seconds" % str(check_after_secs))
        time.sleep(check_after_secs)

        print("STATUS")

        request_params = {"command": "STATUS", "media_id": self.media_id}

        req = requests.get(
            url=X_MEDIA_ENDPOINT_URL, params=request_params, headers=self.headers
        )

        self.processing_info = req.json()["data"].get("processing_info", None)
        self.check_status()

    def send_post_to_twitter(self, post):
        payload = {
            "text": post.title,
            "media": {"media_ids": [self.media_id]},
        }

        req = requests.post(url=X_POST_TO_X_URL, json=payload, headers=self.headers)

        res_json = req.json()
        print(res_json)

    def send_post(self, post):
        self.upload_init(post)
        self.upload_append(post)
        self.upload_finalize()
        self.send_post_to_twitter(post)
        return True
