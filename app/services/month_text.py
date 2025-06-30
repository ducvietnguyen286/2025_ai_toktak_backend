import json
import traceback
import random
from datetime import datetime, timedelta
from app.extensions import db
from app.models.month_text import MonthText
from app.extensions import redis_client
from app.lib.logger import logger


class MonthTextService:

    @staticmethod
    def create_month_text(**kwargs):
        month_text = MonthText(**kwargs)
        db.session.add(month_text)
        db.session.commit()
        return month_text

    @staticmethod
    def insert_month_text(inserts):
        db.session.bulk_save_objects([MonthText(**data) for data in inserts])
        db.session.commit()

    @staticmethod
    def update_month_text_cache(month_key):
        rows = db.session.query(MonthText).filter(MonthText.month == month_key).all()
        month_texts_json = [month_text._to_json() for month_text in rows]

        end_of_month = datetime.now().replace(day=1) + timedelta(days=31)
        end_of_month = end_of_month.replace(day=1) - timedelta(days=1)
        end_of_day_of_month = end_of_month.replace(hour=23, minute=59, second=59)

        logger.info(end_of_day_of_month)
        logger.info(datetime.now())
        logger.info(end_of_day_of_month - datetime.now())
        logger.info(int((end_of_day_of_month - datetime.now()).total_seconds()))

        redis_client.set(
            f"toktak:month_texts_{month_key}",
            json.dumps(month_texts_json),
            ex=int((end_of_month - datetime.now()).total_seconds()),
        )

    @staticmethod
    def random_month_text():
        result = {
            "video": {
                "title": "",
                "comment": "",
                "hashtag": "",
            },
            "image": {
                "comment": "",
                "hashtag": "",
            },
            "blog": "",
        }

        blog_and_comment_count = 10
        hashtag_count = 5
        title_count = 5

        current_month = datetime.now().month
        month_key_search = f"THANG{current_month}"
        redis_key = f"toktak:month_texts_{month_key_search}"

        try:
            raw = redis_client.get(redis_key)
            if not raw:
                MonthTextService.update_month_text_cache(month_key_search)
                raw = redis_client.get(redis_key)

            data = json.loads(raw)

            def sample(field, n):
                return [
                    item[field]
                    for item in random.sample(data, min(n, len(data)))
                    if item.get(field)
                ]

            result["video"]["comment"] = ",".join(
                sample("keyword", blog_and_comment_count)
            )
            result["video"]["title"] = ",".join(sample("keyword", title_count))
            result["video"]["hashtag"] = " ".join(sample("hashtag", hashtag_count))
            result["image"]["comment"] = ",".join(
                sample("keyword", blog_and_comment_count)
            )
            result["image"]["hashtag"] = " ".join(sample("hashtag", hashtag_count))
            result["blog"] = ",".join(sample("keyword", blog_and_comment_count))

            return result

        except Exception as e:
            traceback.print_exc()
            print(e)
            return result
