import os
import threading
import json

from flask_socketio import join_room
from app.lib.logger import log_socket_message
from .extensions import redis_client, socketio


def process_redis_message(message):
    """
    Xử lý dữ liệu nhận được từ Redis.
    Bạn có thể thêm logic tính toán vào đây, rồi emit kết quả qua SocketIO.
    """

    SOCKETIO_PROGRESS_EVENT = os.environ.get("SOCKETIO_PROGRESS_EVENT") or "progress"

    try:
        data = json.loads(message)
        print("Received message from Redis: %s", data)

        batch_id = data.get("batch_id")
        value = data.get("value")
        link_id = data.get("link_id")
        post_id = data.get("post_id")
        status = data.get("status")

        redis_key = f"toktak:progress:{batch_id}:{post_id}"

        progress_json = redis_client.get(redis_key)
        progress = json.loads(progress_json) if progress_json else {}
        if not progress:
            return

        total_link = progress.get("total_link")
        uploads = progress.get("upload")
        total_percent_by_link = 100 // total_link
        percent_by_link_ratio = total_percent_by_link / 100

        total_progress = 0
        total_percent = 0
        is_done = 0

        for upload in uploads:
            upload_link_id = upload.get("link_id")
            upload_post_id = upload.get("post_id")
            upload_status = upload.get("status")
            if (
                (upload_status != "PUBLISHED" and upload_status != "ERRORED")
                and upload_link_id == link_id
                and upload_post_id == post_id
            ):
                percent = int(value) * percent_by_link_ratio

                upload["status"] = status
                upload["value"] = percent
                total_percent += percent

                if status == "PUBLISHED" or status == "ERRORED":
                    total_progress += 1

            elif upload_status == "PUBLISHED" or upload_status == "ERRORED":
                total_progress += 1
                total_percent += int(upload.get("value"))
            else:
                total_percent += int(upload.get("value"))

            if total_progress == total_link:
                is_done = 1
                total_percent = 100

        progress["total_percent"] = total_percent

        if is_done:
            progress["status"] = "PUBLISHED"
        else:
            progress["status"] = "UPLOADING"
            redis_client.set(redis_key, json.dumps(progress), ex=3600)

        print(
            "Emitting progress %s to room %s: %s",
            SOCKETIO_PROGRESS_EVENT,
            batch_id,
            post_id,
        )

        socketio.emit(SOCKETIO_PROGRESS_EVENT, json.dumps(progress), room=batch_id)
    except Exception as e:
        log_socket_message("Error processing Redis message: %s".format(e))


def start_redis_subscriber(app):
    """
    Khởi chạy một thread lắng nghe channel Redis (PROGRESS_CHANNEL) và xử lý message.
    """

    def redis_listener():

        PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

        pubsub = redis_client.pubsub()
        pubsub.subscribe(PROGRESS_CHANNEL)
        log_socket_message(
            "Started Redis subscriber on channel '%s'".format(PROGRESS_CHANNEL)
        )
        for item in pubsub.listen():
            if item.get("type") != "message":
                continue
            message_str = item.get("data").decode("utf-8")
            process_redis_message(message_str)

    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()


@socketio.on("join")
def handle_join(data):
    """
    Cho phép client gửi yêu cầu join room.
    Dữ liệu data phải chứa key 'room' (ví dụ: batch_id)
    """
    room = data.get("room")
    if room:
        join_room(room)
        socketio.emit("join_response", {"msg": f"Joined room {room}"}, room=room)
    else:
        log_socket_message("Room not provided in join event")
