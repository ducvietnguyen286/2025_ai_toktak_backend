from app.lib.logger import (
    log_facebook_message,
    log_instagram_message,
    log_thread_message,
    log_twitter_message,
    log_tiktok_message,
    log_youtube_message,
    log_create_content_message,
    log_advance_run_crawler_message,
    log_socket_message,
    log_make_video_message,
    log_webhook_message,
    log_celery_worker_message,
    log_mongo_database,
    log_reset_user_message,
    log_nice_verify_message,
    log_critical_infrastructure,
    log_critical_database,
    log_critical_security,
    log_critical_emergency_kill,
    log_critical_service_down,
    setup_consumer_logging,
    get_consumer_logger,
)
import logging

def run_all_logs():
    log_facebook_message("Test log facebook")
    log_instagram_message("Test log instagram")
    log_thread_message("Test log thread")
    log_twitter_message("Test log twitter")
    log_tiktok_message("Test log tiktok")
    log_youtube_message("Test log youtube")
    log_create_content_message("Test log create content")
    log_advance_run_crawler_message("Test log advance run crawler")
    log_socket_message("Test log socket")
    log_make_video_message("Test log make video")
    log_webhook_message("Test log webhook")
    log_celery_worker_message("Test log celery worker")
    log_mongo_database("Test log mongo database")
    log_reset_user_message("Test log reset user")
    log_nice_verify_message("Test log nice verify")

    # Critical logs
    log_critical_infrastructure("Test critical infrastructure", component="REDIS", send_alert=False)
    log_critical_database("Test critical database", current_connections=80, max_connections=100)
    log_critical_security("Test security event", ip="127.0.0.1", user_id=123, details="Test details")
    log_critical_emergency_kill(10, 100)
    log_critical_service_down("TestService", error_details="Service crashed")

    # Consumer logger utilities
    class DummyApp:
        logger = logging.getLogger("DummyApp")
    app = DummyApp()
    setup_consumer_logging(app, "TEST_CONSUMER")
    consumer_logger = get_consumer_logger("TEST_CONSUMER")
    consumer_logger.info("Test log from consumer logger")

if __name__ == "__main__":
    run_all_logs()