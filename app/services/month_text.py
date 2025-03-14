from datetime import datetime
import traceback
from app.models.month_text import MonthText


class MonthTextService:

    @staticmethod
    def create_month_text(*args, **kwargs):
        month_text = MonthText(*args, **kwargs)
        month_text.save()
        return month_text

    @staticmethod
    def insert_month_text(inserts):
        month_text = MonthText.objects.insert(inserts)
        return month_text

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

        try:
            video_comment_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": blog_and_comment_count}},
                ]
            )
            video_title_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": title_count}},
                ]
            )
            hastag_video_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": hashtag_count}},
                ]
            )

            image_comment_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": blog_and_comment_count}},
                ]
            )
            hastag_image_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": hashtag_count}},
                ]
            )

            blog_random = MonthText.objects.aggregate(
                [
                    {"$match": {"month": month_key_search}},
                    {"$sample": {"size": blog_and_comment_count}},
                ]
            )

            result["video"]["comment"] = ",".join(
                [item["keyword"] for item in list(video_comment_random)]
            )
            result["video"]["title"] = ",".join(
                [item["keyword"] for item in list(video_title_random)]
            )
            result["video"]["hashtag"] = " ".join(
                [item["hashtag"] for item in list(hastag_video_random)]
            )
            result["image"]["comment"] = ",".join(
                [item["keyword"] for item in list(image_comment_random)]
            )
            result["image"]["hashtag"] = " ".join(
                [item["hashtag"] for item in list(hastag_image_random)]
            )
            result["blog"] = ",".join([item["keyword"] for item in list(blog_random)])

            return result
        except Exception as e:
            traceback.print_exc()
            print(e)
            return result
