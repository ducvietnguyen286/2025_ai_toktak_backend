import json
import os
import traceback
from app.extensions import db
from app.models.batch import Batch
from app.models.post import Post
from app.models.social_post import SocialPost
from datetime import datetime


def import_batch_data(app):
    with app.app_context():
        print("Start Script...")
        json_path = os.path.join(os.getcwd(), "data_scripts", "toktak.batchs.json")
        if not os.path.exists(json_path):
            print(f"File not found: {json_path}")
            return
        post_path = os.path.join(os.getcwd(), "data_scripts", "toktak.posts-new.json")
        if not os.path.exists(post_path):
            print(f"File not found: {post_path}")
            return
        social_path = os.path.join(
            os.getcwd(), "data_scripts", "toktak.social_posts.json"
        )
        if not os.path.exists(social_path):
            print(f"File not found: {post_path}")
            return

        with open(post_path, "r", encoding="utf-8") as f:
            posts_data = json.load(f)
        with open(social_path, "r", encoding="utf-8") as f:
            social_data = json.load(f)

        key_by_batch_id_posts = {}
        for post in posts_data:
            batch_id = post.get("batch_id")
            if batch_id:
                batch_id = (
                    batch_id.get("$oid") if isinstance(batch_id, dict) else batch_id
                )
                if batch_id not in key_by_batch_id_posts:
                    key_by_batch_id_posts[batch_id] = []

                posts = post.get("posts", [])
                key_by_batch_id_posts[batch_id] = posts

        key_by_batch_id_social = {}
        for social in social_data:
            batch_id = social.get("batch_id")
            if batch_id:
                batch_id = (
                    batch_id.get("$oid") if isinstance(batch_id, dict) else batch_id
                )
                if batch_id not in key_by_batch_id_social:
                    key_by_batch_id_social[batch_id] = {}

                social_posts = social.get("social_posts", [])
                for social_post in social_posts:
                    post_id = social_post.get("post_id")
                    post_id = (
                        post_id.get("$oid") if isinstance(post_id, dict) else post_id
                    )
                    if post_id not in key_by_batch_id_social[batch_id]:
                        key_by_batch_id_social[batch_id][post_id] = []

                    key_by_batch_id_social[batch_id][post_id].append(social_post)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                checked_ids = set()
                for item in data:
                    batch_id = item.get("_id")
                    batch_id = (
                        batch_id.get("$oid") if isinstance(batch_id, dict) else batch_id
                    )
                    print(f"Processing batch ID: {batch_id}")
                    if not batch_id or batch_id in checked_ids:
                        continue
                    checked_ids.add(batch_id)
                    created_at_str = item.get("created_at", {}).get("$date")
                    updated_at_str = item.get("updated_at", {}).get("$date")
                    batch = Batch(
                        user_id=item.get("user_id"),
                        url=item.get("url"),
                        shorten_link=item.get("shorten_link", ""),
                        thumbnail=item.get("thumbnail", ""),
                        thumbnails=item.get("thumbnails", "[]"),
                        content=item.get("content", ""),
                        type=item.get("type", 1),
                        count_post=item.get("count_post", 0),
                        done_post=item.get("done_post", 0),
                        status=item.get("status", 1),
                        is_paid_advertisements=item.get("is_paid_advertisements", 0),
                        is_advance=item.get("is_advance", 0),
                        voice_google=item.get("voice_google", 1),
                        process_status=item.get("process_status", "PENDING"),
                        template_info=item.get("template_info", "{}"),
                    )
                    if created_at_str:
                        batch.created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                    if updated_at_str:
                        batch.updated_at = datetime.fromisoformat(
                            updated_at_str.replace("Z", "+00:00")
                        )

                    batch.save()

                    print(f"Batch {batch.id} saved successfully.")

                    posts = key_by_batch_id_posts.get(batch_id, [])
                    social_posts = key_by_batch_id_social.get(batch_id, [])
                    for post in posts:
                        post_id = post.get("_id")
                        post_id = (
                            post_id.get("$oid")
                            if isinstance(post_id, dict)
                            else post_id
                        )

                        if "schedule_date" in post and isinstance(
                            post["schedule_date"], dict
                        ):
                            new_schedule_date = datetime.fromisoformat(
                                post.get("schedule_date", "")
                                .get("$date", "1970-01-01T00:00:00Z")
                                .replace("Z", "+00:00")
                            )
                        else:
                            new_schedule_date = datetime.fromisoformat(
                                post.get("created_at", "")
                                .get("$date", "1970-01-01T00:00:00Z")
                                .replace("Z", "+00:00")
                            )

                        new_post = Post(
                            batch_id=batch.id,
                            user_id=post.get("user_id"),
                            content=post.get("content", ""),
                            thumbnail=post.get("thumbnail", ""),
                            captions=post.get("captions", "[]"),
                            images=post.get("images", "[]"),
                            title=post.get("title", ""),
                            subtitle=post.get("subtitle", ""),
                            description=post.get("description", ""),
                            hashtag=post.get("hashtag", ""),
                            video_url=post.get("video_url", ""),
                            docx_url=post.get("docx_url", ""),
                            file_size=post.get("file_size", 0),
                            mime_type=post.get("mime_type", ""),
                            status_sns=post.get("status_sns", 0),
                            process_number=post.get("process_number", 0),
                            type=post.get("type", ""),
                            render_id=post.get("render_id", ""),
                            video_path=post.get("video_path", ""),
                            social_sns_description=post.get(
                                "social_sns_description", ""
                            ),
                            schedule_date=new_schedule_date,
                            status=post.get("status", 1),
                            created_at=datetime.fromisoformat(
                                post.get("created_at", {})
                                .get("$date", "1970-01-01T00:00:00Z")
                                .replace("Z", "+00:00")
                            ),
                            updated_at=datetime.fromisoformat(
                                post.get("updated_at", {})
                                .get("$date", "1970-01-01T00:00:00Z")
                                .replace("Z", "+00:00")
                            ),
                        )
                        new_post.save()

                        print(f"Post {new_post.id} saved successfully.")

                        if post_id in social_posts:
                            for social in social_posts[post_id]:
                                new_social = SocialPost(
                                    batch_id=batch.id,
                                    user_id=social.get("user_id"),
                                    post_id=new_post.id,
                                    link_id=social.get("link_id", 0),
                                    session_key=social.get("session_key", ""),
                                    social_link=social.get("social_link", ""),
                                    status=social.get("status", ""),
                                    error_message=social.get("error_message", ""),
                                    show_message=social.get("show_message", ""),
                                    disable_comment=social.get("disable_comment", 0),
                                    privacy_level=social.get("privacy_level", ""),
                                    auto_add_music=social.get("auto_add_music", 0),
                                    disable_duet=social.get("disable_duet", 0),
                                    disable_stitch=social.get("disable_stitch", 0),
                                    process_number=social.get("process_number", 0),
                                    instagram_quote=social.get("instagram_quote", ""),
                                    created_at=datetime.fromisoformat(
                                        social.get("created_at", {})
                                        .get("$date", "1970-01-01T00:00:00Z")
                                        .replace("Z", "+00:00")
                                    ),
                                    updated_at=datetime.fromisoformat(
                                        social.get("updated_at", {})
                                        .get("$date", "1970-01-01T00:00:00Z")
                                        .replace("Z", "+00:00")
                                    ),
                                )
                                new_social.save()

                                print(
                                    f"SocialPost {new_social.id} for Post {new_post.id} saved successfully."
                                )

            except Exception as e:
                db.session.rollback()
                traceback.print_exc()
                print(f"Error: {e}")
