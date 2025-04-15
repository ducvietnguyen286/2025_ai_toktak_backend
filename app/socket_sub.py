import os
import threading
import json
from time import sleep
import traceback

from flask_socketio import join_room
from app.lib.logger import log_socket_message
from .extensions import redis_client, socketio

ready_rooms = set()
pending_messages = {}


def process_redis_message(message):
    """
    Xử lý dữ liệu nhận được từ Redis.
    Nếu room chưa sẵn sàng, lưu lại message vào pending_messages.
    Nếu room đã sẵn sàng, emit dữ liệu qua SocketIO ngay.
    """

    SOCKETIO_PROGRESS_EVENT = os.environ.get("SOCKETIO_PROGRESS_EVENT") or "progress"

    try:
        data = json.loads(message)
        print("Received message from Redis: %s", data)

        sync_id = data.get("sync_id", "")
        batch_id = data.get("batch_id")
        user_id = data.get("user_id")
        value = data.get("value")
        link_id = data.get("link_id")
        post_id = data.get("post_id")
        social_link = data.get("social_link")
        status = data.get("status")

        room = sync_id if sync_id != "" else batch_id + "_" + user_id

        if sync_id == "":
            redis_key = f"toktak:progress:{room}:{post_id}"

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
                    upload["social_link"] = social_link
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
        else:
            redis_key = f"toktak:progress-sync:{sync_id}"
            progress_json = redis_client.get(redis_key)
            progress = json.loads(progress_json) if progress_json else {}
            if not progress:
                return

            total_post = progress.get("total_post")
            uploads = progress.get("upload")
            total_percent_by_post = 100 // total_post
            percent_by_post_ratio = total_percent_by_post / 100

            total_progress = 0
            total_percent = 0
            is_done = 0

            for upload in uploads:
                upload_post_id = upload.get("post_id")
                upload_status = upload.get("status")

                if upload_status != "PUBLISHED" and upload_status != "ERRORED":
                    percent = int(value) * percent_by_post_ratio

                    upload["status"] = status
                    upload["self_value"] = int(value)
                    upload["value"] = percent
                    upload["social_link"] = social_link
                    total_percent += percent

                    if status == "PUBLISHED" or status == "ERRORED":
                        total_progress += 1

                elif upload_status == "PUBLISHED" or upload_status == "ERRORED":
                    total_progress += 1
                    total_percent += int(upload.get("value"))
                else:
                    total_percent += int(upload.get("value"))

                if total_progress == total_post:
                    is_done = 1
                    total_percent = 100

            if is_done:
                progress["status"] = "PUBLISHED"
            else:
                progress["status"] = "UPLOADING"
                redis_client.set(redis_key, json.dumps(progress), ex=3600)

        progress_json_str = json.dumps(progress)
        if room not in ready_rooms:
            pending_messages.setdefault(room, []).append(progress_json_str)
            return

        print(
            f"Emitting progress {SOCKETIO_PROGRESS_EVENT} to room {room}",
        )
        socketio.emit(SOCKETIO_PROGRESS_EVENT, json.dumps(progress), room=room)
        return
    except Exception as e:
        log_socket_message(f"Error processing Redis message: {e}")
        traceback.print_exc()
        return


def start_redis_subscriber(app):
    """
    Khởi chạy một thread lắng nghe channel Redis (PROGRESS_CHANNEL) và xử lý message.
    """

    def redis_listener():
        with app.app_context():
            PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

            pubsub = redis_client.pubsub()
            pubsub.subscribe(PROGRESS_CHANNEL)
            log_socket_message(
                f"Started Redis subscriber on channel '{PROGRESS_CHANNEL}'"
            )
            for item in pubsub.listen():
                if item.get("type") != "message":
                    continue
                message_str = item.get("data").decode("utf-8")
                process_redis_message(message_str)

    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()


def start_notification_subscriber(app):
    """
    Khởi chạy một thread lắng nghe channel Redis (NOTIFICATION_CHANNEL) và xử lý message.
    """

    def redis_listener():
        with app.app_context():
            NOTIFICATION_CHANNEL = (
                os.environ.get("REDIS_NOTIFICATION_CHANNEL") or "progessbar"
            )

            pubsub = redis_client.pubsub()
            pubsub.subscribe(NOTIFICATION_CHANNEL)
            log_socket_message(
                f"Started Redis subscriber on channel '{NOTIFICATION_CHANNEL}'"
            )
            for item in pubsub.listen():
                if item.get("type") != "message":
                    continue
                message_str = item.get("data").decode("utf-8")
                process_redis_message(message_str)

    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()


@socketio.on("ready-to-listen")
def handle_ready_to_listen(data):
    """
    Cho phép client gửi yêu cầu bắt đầu nghe sự kiện emit từ server trả về.
    Dữ liệu data phải chứa key 'room' (ví dụ: batch_id, sync_id)
    """
    room = data.get("room")
    if room:
        ready_rooms.add(room)
        socketio.emit(
            "comfirmed", {"msg": f"Ready Listen message from {room}"}, room=room
        )
        messages = pending_messages.pop(room, [])
        SOCKETIO_PROGRESS_EVENT = (
            os.environ.get("SOCKETIO_PROGRESS_EVENT") or "progress"
        )
        for message in messages:
            message = json.loads(message)
            socketio.emit(SOCKETIO_PROGRESS_EVENT, message, room=room)
            sleep(0.1)
    else:
        log_socket_message("Room not provided in join event")


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
