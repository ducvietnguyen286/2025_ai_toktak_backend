import os
import threading
import json

from flask_socketio import join_room
from app.lib.logger import logger
from .extensions import redis_client, socketio


def process_redis_message(message, app):
    """
    Xử lý dữ liệu nhận được từ Redis.
    Bạn có thể thêm logic tính toán vào đây, rồi emit kết quả qua SocketIO.
    """

    SOCKETIO_PROGRESS_EVENT = os.environ.get("SOCKETIO_PROGRESS_EVENT") or "progress"

    try:
        data = json.loads(message)
        logger.info("Received message from Redis: %s", data)
        print("Received message from Redis: %s", data)

        batch_id = data.get("batch_id")
        value = data.get("value")
        link_id = data.get("link_id")
        post_id = data.get("post_id")
        status = data.get("status")

        progress_json = redis_client.get(f"toktak:progress:{batch_id}")
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

        progress["total_percent"] = total_percent

        if is_done:
            total_percent = 100
            progress["status"] = "PUBLISHED"
        else:
            progress["status"] = "UPLOADING"
            redis_client.set(
                f"toktak:progress:{batch_id}", json.dumps(progress), ex=3600
            )

        logger.info(
            "Emitting progress %s to room %s: %s",
            SOCKETIO_PROGRESS_EVENT,
            batch_id,
            progress,
        )

        print(
            "Emitting progress %s to room %s: %s",
            SOCKETIO_PROGRESS_EVENT,
            batch_id,
            post_id,
        )

        socketio.emit(SOCKETIO_PROGRESS_EVENT, json.dumps(progress), room=batch_id)
    except Exception as e:
        app.logger.error("Error processing Redis message: %s", e)


def start_redis_subscriber(app):
    """
    Khởi chạy một thread lắng nghe channel Redis (PROGRESS_CHANNEL) và xử lý message.
    """

    def redis_listener():

        PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

        pubsub = redis_client.pubsub()
        pubsub.subscribe(PROGRESS_CHANNEL)
        logger.info("Started Redis subscriber on channel '%s'", PROGRESS_CHANNEL)
        for item in pubsub.listen():
            if item.get("type") != "message":
                continue
            message_str = item.get("data").decode("utf-8")
            process_redis_message(message_str, app)

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
        logger.error("Room not provided in join event")
