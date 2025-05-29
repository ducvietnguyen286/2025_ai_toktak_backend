import base64
import os
import time
import traceback
import requests

from app.lib.header import generate_desktop_user_agent

CLIENT_ID = "dFJXTjZncWNyU0NuanNNS0N2VF86MTpjaQ"
CLIENT_SECRET = "Y4lLwcxkuyfYRBEUVpMWTR-_qH1fNMbAYYyZk35YXe6prHmq5q"

MEDIA_ENDPOINT_URL = "https://api.twitter.com/2/media/upload"
X_POST_TO_X_URL = "https://api.x.com/2/tweets"
TOKEN_URL = "https://api.x.com/2/oauth2/token"

access_token = "dXg0dE5rTFN0ckk1V2ozYzhNUEVjcTI3R3liWmN3U3pkR3duXzFQeW85akxuOjE3NDg1MDIxMTE1MTc6MTowOmF0OjE"
refresh_token = "XzNzYzZaLTZEYm1VcGx3WXk2RzBBUXl5R0hLYmNFZVlHcGJRUTBKeWdldWRuOjE3NDg0OTY1MjU1Nzc6MTowOnJ0OjE"


def get_media_content(media_url, is_photo=False, get_content=True):
    session = requests.Session()
    print(f"------------ GET MEDIA : {media_url}----------------")
    try:
        headers = {
            "Accept": "video/*" if not is_photo else "image/*",
            "User-Agent": generate_desktop_user_agent(),
        }
        with session.get(
            media_url, headers=headers, timeout=(10, 120), stream=True
        ) as response:
            print("------------ START STREAMING----------------")
            response.raise_for_status()

            media_size = int(response.headers.get("content-length"))
            media_type = response.headers.get("content-type")

            content = b"".join(
                chunk for chunk in response.iter_content(chunk_size=2048)
            )
            if get_content:
                return content
            print("------------ GET MEDIA SUCCESSFULLY----------------")
            return {
                "content": content,
                "media_size": media_size,
                "media_type": media_type,
            }

    except Exception as e:
        traceback.print_exc()
        print(f"SEND POST MEDIA - GET MEDIA URL: {str(e)}")
        return False


def refresh_token_func():
    print("Refreshing access token...")
    credentials_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }

    r_data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=r_data)
    data = response.json()

    return {"status": "success", "result": data}


def upload_media(media_url, is_photo=False):
    print(f"Uploading media from URL: {media_url}, is_photo: {is_photo}")
    media_content = get_media_content(media_url, is_photo=is_photo, get_content=False)
    if not media_content:
        return {"status": "error", "message": "Failed to get media content"}

    media_type = media_content.get("media_type")
    media_cateogry = "tweet_image" if is_photo else "tweet_video"
    media_size = media_content.get("media_size")

    print(
        f"Media type: {media_type}, Category: {media_cateogry}, Size: {media_size} bytes"
    )
    init_data = initial_upload(
        media_type=media_type,
        media_category=media_cateogry,
        media_size=media_size,
    )

    if init_data.get("status") == "error":
        print(f"Error initializing upload: {init_data.get('message')}")
        return False
    media_id = init_data.get("media_id")
    append_data = append_upload(
        media_id=media_id,
        media_content=media_content.get("content"),
        total_bytes=media_size,
    )
    if append_data.get("status") == "error":
        print(f"Error appending upload: {append_data.get('message')}")
        return False

    print(f"Media upload appended successfully, media ID: {media_id}")

    while True:
        status_data = get_status_upload(media_id=media_id)
        processing_info = status_data.get("processing_info", {})
        if processing_info.get("state") == "in_progress":
            check_after_secs = processing_info.get("check_after_secs", 5)
            progress_percent = processing_info.get("progress_percent", 0)
            print(f"Upload progress: {progress_percent}%")
            print("Upload in progress, waiting...")
            time.sleep(check_after_secs)
        else:
            print(f"Upload status: {processing_info}")
            print("Upload completed or failed")
            break

    finalize_data = finalize_upload(media_id=media_id)
    if finalize_data.get("status") == "error":
        print(f"Error finalizing upload: {finalize_data.get('message')}")
        return False

    print("Media upload finalized successfully")
    return media_id


def initial_upload(media_type, media_category, media_size):
    print(
        f"Initializing upload for media type: {media_type}, category: {media_category}, size: {media_size} bytes"
    )
    url = f"{MEDIA_ENDPOINT_URL}/initialize"

    payload = {
        "media_category": media_category,
        "media_type": media_type,
        "shared": False,
        "total_bytes": media_size,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    print(f"Response initial: {response.status_code}, {response.text}")

    if response.status_code != 200:
        print(f"Error starting upload: {response.status_code} - {response.text}")
        return {"status": "error", "message": "Failed to start media upload"}

    response_data = response.json()
    data = response_data.get("data", {})
    media_id = data.get("id")
    media_key = data.get("media_key")
    return {"status": "success", "media_id": media_id, "media_key": media_key}


def append_upload(media_id, media_content, total_bytes):
    print(f"Appending upload for media ID: {media_id}, total bytes: {total_bytes}")
    url = f"{MEDIA_ENDPOINT_URL}/{media_id}/append"
    segment_id = 0
    bytes_sent = 0
    chunk_size = 4 * 1024 * 1024  # 4MB chunk size

    while bytes_sent < total_bytes:
        chunk = media_content[bytes_sent : bytes_sent + chunk_size]
        files = {"media": ("chunk", chunk)}

        data = {
            "segment_index": segment_id,
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

        print(f"Response append: {response.status_code}, {response.text}")

        print(
            f"Uploaded segment {segment_id} of size {len(chunk)} bytes, total sent: {bytes_sent + len(chunk)} bytes"
        )
        segment_id += 1
        bytes_sent += len(chunk)

    return {"status": "success", "message": "Media uploaded successfully"}


def finalize_upload(media_id):
    print(f"Finalizing upload for media ID: {media_id}")
    url = f"{MEDIA_ENDPOINT_URL}/{media_id}/finalize"

    headers = {"Authorization": "Bearer access_token"}

    response = requests.request("POST", url, headers=headers)

    print(f"Response finalize: {response.status_code}, {response.text}")

    response.raise_for_status()
    return response.json()["data"]


def get_status_upload(media_id):
    print(f"Getting status for media ID: {media_id}")

    headers = {"Authorization": f"Bearer {access_token}"}

    params = {"media_id": media_id, "command": "STATUS"}

    response = requests.request(
        "GET", MEDIA_ENDPOINT_URL, headers=headers, params=params
    )

    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error getting status: {response.status_code} - {response.text}")
        return {"status": "error", "message": "Failed to get media status"}

    response.raise_for_status()
    return response.json()["data"]


if __name__ == "__main__":
    media_url = "https://shotstack-api-v1-output.s3.ap-southeast-2.amazonaws.com/nwu2zf6syl/e9ddf1dd-4803-47ae-a099-c0fee952ad99.mp4"
    media_id = upload_media(media_url, is_photo=False)
    print(f"Upload completed. Media ID: {media_id}")
