from app.lib.logger import log_advance_run_crawler_message
from app.scraper import Scraper
from app.services.batch import BatchService
from app.services.notification import NotificationServices
from app.services.user import UserService
from app.services.shorten_services import ShortenServices
from app.ais.chatgpt import call_chatgpt_clear_product_name
from app.extensions import db, redis_client
from app.enums.messages import MessageError
import const
import json


class CrawlAdvance:
    def __init__(self, batch_id, url):
        self.batch_id = batch_id
        self.url = url
        self.app = None

    def update_redis_batch(self, batch):
        batch_id = batch.id
        if batch:
            redis_client.set(
                f"toktak:batch:{batch_id}",
                json.dumps(batch._to_json()),
                ex=60 * 60 * 24,
            )

    def update_batch_error_analyze(self, batch_id):
        try:
            batch = BatchService.update_batch(
                batch_id,
                process_status=const.BATCH_PROCESSING_STATUS["FAILED"],
                error_code="201",
                message=MessageError.NO_ANALYZE_URL.value["message"],
                error_message=MessageError.NO_ANALYZE_URL.value["error_message"],
            )
            self.update_redis_batch(batch)
        except Exception as e:
            log_advance_run_crawler_message(f"Error updating batch: {e}")
            return None

    def update_batch_processing(self, batch_id):
        try:
            batch = BatchService.update_batch(
                batch_id, process_status=const.BATCH_PROCESSING_STATUS["CRAWLING"]
            )
            self.update_redis_batch(batch)
        except Exception as e:
            log_advance_run_crawler_message(f"Error updating batch: {e}")
            return None

    def crawl_advance(self, app):
        try:
            with app.app_context():
                self.app = app
                batch_id = self.run_crawl_advance()
                if not batch_id:
                    return False

            return True
        except Exception as e:
            log_advance_run_crawler_message(f"Error in create_content: {e}")
            return False

    def run_crawl_advance(self):
        try:
            batch_id = self.batch_id
            batch = BatchService.find_batch(batch_id)

            log_advance_run_crawler_message(f"Run Crawler {batch_id}")

            if not batch:
                log_advance_run_crawler_message("ERROR: Batch not found")
                return False

            if batch.is_advance == 0:
                log_advance_run_crawler_message("ERROR: Batch is not advance")
                return False

            url = self.url
            if not url:
                log_advance_run_crawler_message("ERROR: Url is not found")
                return False

            data = Scraper().scraper({"url": url, "batch_id": batch_id})

            user_id = batch.user_id

            if not data:
                NotificationServices.create_notification(
                    user_id=user_id,
                    status=const.NOTIFICATION_FALSE,
                    title=f"❌ 해당 {url} 은 분석이 불가능합니다. 올바른 링크인지 확인해주세요.",
                    description=f"Scraper False {url}",
                )

                redis_user_batch_key = f"toktak:users:batch_remain:{user_id}"
                user = UserService.find_user(user_id)
                redis_client.set(redis_user_batch_key, user.batch_remain + 1, ex=180)

                BatchService.update_batch(
                    batch_id,
                    process_status=const.BATCH_PROCESSING_STATUS["FAILED"],
                    error_code="201",
                    message=MessageError.NO_ANALYZE_URL.value["message"],
                    error_message=MessageError.NO_ANALYZE_URL.value["error_message"],
                )

                redis_client.set(
                    f"toktak:batch:{batch_id}",
                    json.dumps(batch._to_json()),
                    ex=60 * 60 * 24,
                )

                return False

            thumbnail_url = data.get("image", "")
            thumbnails = data.get("thumbnails", [])

            shorten_link, is_shorted = ShortenServices.shorted_link(url)
            data["base_url"] = shorten_link
            data["shorten_link"] = shorten_link if is_shorted else ""

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                data["name"] = product_name_cleared

            BatchService.update_batch(
                batch_id,
                thumbnail=thumbnail_url,
                thumbnails=json.dumps(thumbnails),
                base_url=shorten_link,
                shorten_link=shorten_link,
                content=json.dumps(data),
            )

            return True
        except Exception as e:
            log_advance_run_crawler_message(f"ERROR: Error create batch: {str(e)}")
            return False
