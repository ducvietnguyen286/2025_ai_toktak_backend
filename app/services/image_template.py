import json

from sqlalchemy import asc
from app.ais.chatgpt import call_chatgpt_get_main_text_and_color_for_image
from app.makers.images import ImageMaker
from app.models.image_template import ImageTemplate
from app.lib.query import (
    select_with_filter,
    select_by_id,
    select_with_pagination,
    select_with_filter_one,
    update_by_id,
)


class ImageTemplateService:

    @staticmethod
    def create_image_template(*args, **kwargs):
        image_template = ImageTemplate(*args, **kwargs)
        image_template.save()
        return image_template

    @staticmethod
    def find_image_template(id):
        return select_by_id(ImageTemplate, id)

    @staticmethod
    def find_image_template_by_template_code(template_code):
        return select_with_filter_one(
            ImageTemplate, filters=[ImageTemplate.template_code == template_code]
        )

    @staticmethod
    def find_image_template_by_type(type):
        return select_with_filter_one(
            ImageTemplate, filters=[ImageTemplate.type == type]
        )

    @staticmethod
    def get_image_templates():
        templates = select_with_filter(
            ImageTemplate,
            filters=[ImageTemplate.status == "ACTIVE"],
            order_by=[asc(ImageTemplate.sort)],
        )
        return [t._to_json() for t in templates]

    @staticmethod
    def get_not_json_image_templates():
        return select_with_filter(
            ImageTemplate, filters=[ImageTemplate.status == "ACTIVE"]
        )

    @staticmethod
    def update_image_template(id, **kwargs):
        return update_by_id(ImageTemplate, id, kwargs)

    @staticmethod
    def delete_image_template(id):
        template = select_by_id(ImageTemplate, id)
        if template:
            template.delete()
            return True
        return False

    @staticmethod
    def create_image_by_template(
        template, captions, process_images, post, is_avif=False
    ):
        template_type = template.type
        random_key = []
        for key, value in template._to_json().items():
            if value == "random_color":
                random_key.append(key)
        random_key_str = ",".join(random_key)
        first_caption = captions[0] if len(captions) > 0 else ""
        response_color = call_chatgpt_get_main_text_and_color_for_image(
            first_caption, random_key_str, post.id
        )

        image_urls = []
        other_images = []
        other_captions = []
        file_size = 0

        if response_color:
            parse_color = json.loads(response_color)

            if template_type == "TEMPLATE_IMAGE_1":
                res_visual = ImageTemplateService.create_image_by_template_image_1(
                    template, captions, parse_color, post.batch_id
                )
                image_urls.append(res_visual["image_url"])
                file_size += res_visual["file_size"]
                other_images = process_images[0:-1]
                other_captions = captions[1:]

            elif template_type == "TEMPLATE_IMAGE_2":
                res_visual = ImageTemplateService.create_image_by_template_image_2(
                    template,
                    process_images,
                    captions,
                    parse_color,
                    post.batch_id,
                    is_avif=is_avif,
                )
                image_urls.append(res_visual["image_url"])
                file_size += res_visual["file_size"]
                other_images = process_images[1:]
                other_captions = captions[1:]

            elif template_type == "TEMPLATE_IMAGE_3":
                res_visual = ImageTemplateService.create_image_by_template_image_3(
                    template,
                    process_images,
                    captions,
                    parse_color,
                    post.batch_id,
                    is_avif=is_avif,
                )
                image_urls.append(res_visual["image_url"])
                file_size += res_visual["file_size"]
                other_images = process_images[1:]
                other_captions = captions[1:]

        for index, image_url in enumerate(other_images):
            image_caption = other_captions[index] if index < len(other_captions) else ""
            res_img = ImageMaker.save_image_and_write_text_advance(
                image_url,
                image_caption,
                font_size=80,
                batch_id=post.batch_id,
                is_avif=is_avif,
            )
            image_urls.append(res_img["image_url"])
            file_size += res_img["file_size"]

        return {
            "image_urls": image_urls,
            "file_size": file_size,
            "mime_type": "image/jpeg",
        }

    @staticmethod
    def create_image_by_template_image_1(template, captions, parse_color, batch_id=0):
        first_caption = captions[0] if len(captions) > 0 else ""

        main_text = parse_color.get("main_text")
        main_color = parse_color.get("main_text_color")
        background_color = parse_color.get("background_color")

        res_visual = ImageMaker.make_image_by_template_image_1(
            template,
            first_caption,
            main_text,
            main_color,
            background_color,
            batch_id,
        )

        return res_visual

    @staticmethod
    def create_image_by_template_image_2(
        template, process_images, captions, parse_color, batch_id, is_avif=False
    ):
        first_image = process_images[0]
        first_caption = captions[0] if len(captions) > 0 else ""

        main_text = parse_color.get("main_text")
        main_color = parse_color.get("main_text_color")

        res_visual = ImageMaker.make_image_by_template_image_2(
            template=template,
            first_image=first_image,
            first_caption=first_caption,
            main_text=main_text,
            main_color=main_color,
            batch_id=batch_id,
            is_avif=is_avif,
        )

        return res_visual

    @staticmethod
    def create_image_by_template_image_3(
        template, process_images, captions, parse_color, batch_id, is_avif=False
    ):
        first_image = process_images[0]
        first_caption = captions[0] if len(captions) > 0 else ""

        main_text = parse_color.get("main_text")
        main_color = parse_color.get("main_text_color")

        res_visual = ImageMaker.make_image_by_template_image_3(
            template=template,
            first_image=first_image,
            first_caption=first_caption,
            main_text=main_text,
            main_color=main_color,
            batch_id=batch_id,
            is_avif=is_avif,
        )

        return res_visual
