import os
import time
import datetime
from urllib.parse import urlparse
import uuid
from PIL import Image, ImageDraw, ImageFont
import requests
import cv2

from app.lib.header import generate_desktop_user_agent


date_create = datetime.datetime.now().strftime("%Y_%m_%d")
UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FONT_FOLDER = os.path.join(os.getcwd(), "app/makers/fonts")
CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"


def wrap_text_by_pixel(draw, text, font, max_width):
    """
    Tự động cắt chuỗi `text` thành nhiều dòng dựa trên độ rộng (pixel) tối đa `max_width`.
    - draw: ImageDraw object
    - text: Chuỗi cần hiển thị
    - font: Font đang dùng
    - max_width: Chiều rộng tối đa (pixel) cho mỗi dòng
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # Nếu current_line đang trống, gán thẳng word,
        # nếu không thì ghép thêm khoảng trắng + word
        test_line = word if not current_line else (current_line + " " + word)

        # Đo chiều rộng dòng test_line
        line_width = draw.textlength(test_line, font=font)

        if line_width <= max_width:
            # Nếu còn đủ chỗ, cập nhật current_line
            current_line = test_line
        else:
            # Nếu vượt quá max_width, đưa current_line vào lines, bắt đầu dòng mới
            lines.append(current_line)
            current_line = word

    # Thêm dòng cuối cùng (nếu có) vào lines
    if current_line:
        lines.append(current_line)

    return lines


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = word if not current_line else (current_line + " " + word)
        test_width = draw.textlength(test_line, font=font)

        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append((current_line, None))  # Màu None để kế thừa màu của text gốc
            current_line = word

    if current_line:
        lines.append((current_line, None))

    return lines


class ImageMaker:

    @staticmethod
    def save_images(images):
        image_paths = []
        for index, image_url in enumerate(images):
            image_url = ImageMaker.save_image_url(image_url)
            image_paths.append(image_url)
        return image_paths

    @staticmethod
    def save_image_and_write_text_advance(
        image_url,
        text,
        font_size=50,
        margin=(90, 50, 90, 160),
        text_color=(0, 0, 0),  # Trắng
        stroke_color=(255, 255, 255),  # Màu viền (đen)
        stroke_width=10,  # Độ dày viền
        target_size=(1080, 1350),
    ):
        image_path = ImageMaker.save_image_url_get_path(image_url)
        image_name = image_path.split("/")[-1]

        while not os.path.exists(image_path):
            time.sleep(0.5)

        try:
            image = Image.open(image_path)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}",
            }

        image = image.convert("RGB")

        image_width, image_height = target_size
        image_ratio = image_width / image_height

        if image.height > image.width:
            crop_height = int(image.width / image_ratio)
            top = (image.height - crop_height) // 2
            bottom = top + crop_height
            image = image.crop((0, top, image.width, bottom))
            image = image.resize(target_size, Image.LANCZOS)
        else:
            new_width = image_width
            new_height = int(image.height * (image_width / image.width))
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            background = Image.new("RGBA", target_size, (0, 0, 0, 255))
            top = (image_height - new_height) // 2
            background.paste(resized_image, (0, top))
            image = background
            image = image.convert("RGB")

        # Resize ảnh về kích thước chuẩn (1080x1080) với chất lượng cao
        image = image.resize(target_size, Image.LANCZOS)

        # Tạo đối tượng vẽ
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(f"{FONT_FOLDER}/CookieRun.ttf", font_size)
        except IOError:
            print(f"Không tìm thấy font CookieRun.ttf, sử dụng font mặc định.")
            font = ImageFont.load_default()

        # Tính vùng giới hạn chữ
        left_margin, top_margin, right_margin, bottom_margin = margin
        max_width = image.width - left_margin - right_margin

        # Tự động cắt xuống dòng theo pixel
        lines = wrap_text_by_pixel(draw, text, font, max_width)
        wrapped_text = "\n".join(lines)

        # Tính kích thước text
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

        bottom_margin = 220
        # Tính toán vị trí để đặt text xuống bottom của ảnh
        text_y = image.height - bottom_margin - text_height

        # Vẽ multiline text tại vị trí (left_margin, top_margin)
        draw.multiline_text(
            (left_margin, text_y),
            wrapped_text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color,
        )

        if not (
            image_path.lower().endswith(".jpg")
            or image_path.lower().endswith(".jpeg")
            or image_path.lower().endswith(".webp")
        ):
            os.remove(image_path)

            image_name = image_name.rsplit(".", 1)[0] + ".jpg"
            image_path = image_path.rsplit(".", 1)[0] + ".jpg"
        image.save(image_path)

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }

    @staticmethod
    def make_image_by_template_image_3(
        template,
        first_image,
        first_caption,
        main_text,
        main_color,
        target_size=(1080, 1350),
    ):
        image_path = ImageMaker.make_resize_image(first_image, target_size)
        image_name = image_path.split("/")[-1]
        try:
            background = cv2.imread(image_path)
            background = cv2.cvtColor(background, cv2.COLOR_BGR2RGB)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}",
            }
        background_pil = Image.fromarray(background)
        image = ImageMaker.draw_text_to_image_bottom(
            base_text=first_caption,
            image=background_pil,
            main_text=main_text,
            main_text_color=main_color,
            font_path=template.font_path,
            font_size=template.font_size,
            margin=f"({template.margin})",
            text_color=template.text_color,
            stroke_color=template.stroke_color,
            stroke_width=template.stroke_width,
            bottom_margin=300,
        )
        image.save(image_path)
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }

    @staticmethod
    def make_image_by_template_image_2(
        template,
        first_image,
        first_caption,
        main_text,
        main_color,
        target_size=(1080, 1350),
    ):
        image_path = ImageMaker.make_resize_image(first_image, target_size)
        image_name = image_path.split("/")[-1]

        try:
            background = cv2.imread(image_path)
            background = cv2.GaussianBlur(background, (35, 35), 0)  # Làm mờ nền
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}",
            }
        background_pil = Image.fromarray(cv2.cvtColor(background, cv2.COLOR_BGR2RGB))

        image = ImageMaker.draw_text_to_image_center(
            base_text=first_caption,
            image=background_pil,
            main_text=main_text,
            main_text_color=main_color,
            font_path=template.font_path,
            font_size=template.font_size,
            margin=f"({template.margin})",
            text_color=template.text_color,
            stroke_color=template.stroke_color,
            stroke_width=template.stroke_width,
        )

        image.save(image_path)
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }

    @staticmethod
    def make_resize_image(image, target_size):
        image_path = ImageMaker.save_image_url_get_path(image)
        image_name = image_path.split("/")[-1]

        while not os.path.exists(image_path):
            time.sleep(0.5)

        try:
            image = Image.open(image_path)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}",
            }

        image = image.convert("RGB")

        image_width, image_height = target_size
        image_ratio = image_width / image_height

        if image.height > image.width:
            crop_height = int(image.width / image_ratio)
            top = (image.height - crop_height) // 2
            bottom = top + crop_height
            image = image.crop((0, top, image.width, bottom))
            image = image.resize(target_size, Image.LANCZOS)
        else:
            new_width = image_width
            new_height = int(image.height * (image_width / image.width))
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            background = Image.new("RGBA", target_size, (0, 0, 0, 255))
            top = (image_height - new_height) // 2
            background.paste(resized_image, (0, top))
            image = background
            image = image.convert("RGB")

        if not (
            image_path.lower().endswith(".jpg")
            or image_path.lower().endswith(".jpeg")
            or image_path.lower().endswith(".webp")
        ):
            os.remove(image_path)

            image_name = image_name.rsplit(".", 1)[0] + ".jpg"
            image_path = image_path.rsplit(".", 1)[0] + ".jpg"
        image.save(image_path)

        return image_path

    @staticmethod
    def make_image_by_template_image_1(
        template,
        first_caption,
        main_text,
        main_color,
        background_color,
        target_size=(1080, 1350),
    ):
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        image_name = f"{timestamp}_{unique_id}.jpg"

        image_path = f"{UPLOAD_FOLDER}/{image_name}"
        image_width, image_height = target_size

        image = Image.new("RGB", (image_width, image_height), background_color)

        image = ImageMaker.draw_text_to_image_center(
            base_text=first_caption,
            image=image,
            main_text=main_text,
            main_text_color=main_color,
            font_path=template.font_path,
            font_size=template.font_size,
            margin=f"({template.margin})",
            text_color=template.text_color,
            stroke_color=template.stroke_color,
            stroke_width=template.stroke_width,
        )

        image.save(image_path)
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }

    @staticmethod
    def draw_text_to_image_bottom(
        base_text,
        image,
        main_text,
        main_text_color,
        font_path,
        font_size,
        margin,
        text_color,
        stroke_color,
        stroke_width,
        bottom_margin,
    ):
        print(f"Draw text to image: {margin}")
        if type(margin) == str:
            margin = tuple(map(int, margin.strip("()").split(",")))

        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Không tìm thấy font dotum.ttc, sử dụng font mặc định.")
            font = ImageFont.load_default()

        left_margin, top_margin, right_margin, bottom_margin = margin
        max_width = image.width - left_margin - right_margin

        if main_text in base_text:
            before_main, after_main = base_text.split(main_text, 1)
            text_list = [
                (before_main, text_color),
                (main_text, main_text_color),
                (after_main, text_color),
            ]
        else:
            text_list = [(base_text, text_color)]

        all_lines = []
        for text, color in text_list:
            wrapped_lines = wrap_text(draw, text, font, max_width)
            all_lines.extend(
                [(line, color if c is None else c) for line, c in wrapped_lines]
            )

        # Tính tổng chiều cao văn bản chính xác
        ascent, descent = font.getmetrics()  # Lấy chiều cao dòng thực tế
        line_height = ascent + descent  # Tổng chiều cao của mỗi dòng
        line_spacing = 60  # Khoảng cách giữa các dòng
        total_text_height = (
            len(all_lines) * line_height + (len(all_lines) - 1) * line_spacing
        )

        text_y = image.height - bottom_margin - total_text_height

        for line, color in all_lines:
            text_width = draw.textlength(line, font=font)
            text_x = (image.width - text_width) // 2  # Căn giữa
            draw = ImageMaker.draw_text_with_outline(
                draw,
                line,
                (text_x, text_y),
                font,
                color,
                stroke_color,
                stroke_width,
            )
            text_y += line_height + 60  # Khoảng cách giữa các dòng

        return image

    @staticmethod
    def draw_text_to_image_center(
        base_text,
        image,
        main_text,
        main_text_color,
        font_path,
        font_size,
        margin,
        text_color,
        stroke_color,
        stroke_width,
    ):
        print(f"Draw text to image: {margin}")
        if type(margin) == str:
            margin = tuple(map(int, margin.strip("()").split(",")))

        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Không tìm thấy font dotum.ttc, sử dụng font mặc định.")
            font = ImageFont.load_default()

        # Tính vùng giới hạn chữ
        left_margin, top_margin, right_margin, bottom_margin = margin
        max_width = image.width - left_margin - right_margin

        if main_text in base_text:
            before_main, after_main = base_text.split(main_text, 1)
            text_list = [
                (before_main, text_color),
                (main_text, main_text_color),
                (after_main, text_color),
            ]
        else:
            text_list = [(base_text, text_color)]

        all_lines = []
        for text, color in text_list:
            wrapped_lines = wrap_text(draw, text, font, max_width)
            all_lines.extend(
                [(line, color if c is None else c) for line, c in wrapped_lines]
            )

        line_height = font.getbbox("A")[3] - font.getbbox("A")[1]
        total_text_height = len(all_lines) * line_height + 60 * (len(all_lines) - 1)

        # Tính toán vị trí bắt đầu (Căn giữa theo chiều dọc)
        start_y = (image.height - total_text_height) // 2

        for line, color in all_lines:
            text_width = draw.textlength(line, font=font)
            text_x = (image.width - text_width) // 2
            draw = ImageMaker.draw_text_with_outline(
                draw,
                line,
                (text_x, start_y),
                font,
                color,
                stroke_color,
                stroke_width,
            )
            start_y += line_height + 60

        return image

    @staticmethod
    def draw_text_with_outline(
        draw, text, position, font, text_color, outline_color, outline_thickness
    ):
        x, y = position
        for dx in range(-outline_thickness, outline_thickness + 1):
            for dy in range(-outline_thickness, outline_thickness + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=text_color)
        return draw

    @staticmethod
    def save_image_from_request(file):
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        file_name = file.filename
        file_ext = file_name.split(".")[-1]

        file_save_name = f"{timestamp}_{unique_id}.{file_ext}"
        file_path = f"{UPLOAD_FOLDER}/{file_save_name}"

        file.save(file_path)

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{file_save_name}"
        return image_url

    @staticmethod
    def save_image_url(image_url):
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        image_ext = image_url.split(".")[-1]
        image_name = f"{timestamp}_{unique_id}.{image_ext}"

        image_path = f"{UPLOAD_FOLDER}/{image_name}"
        with open(image_path, "wb") as image_file:
            image_file.write(requests.get(image_url).content)
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"
        return image_url

    @staticmethod
    def save_image_url_get_path(image_url):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        print(f"Downloading image from {image_url}")
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        url_parsed = urlparse(image_url)
        path = url_parsed.path

        if "." in path:
            image_ext = path.split(".")[-1]
        else:
            image_ext = "jpg"

        if "?" in image_ext:
            image_ext = image_ext.split("?")[0]

        if not image_ext:
            image_ext = "jpg"

        image_name = f"{timestamp}_{unique_id}.{image_ext}"

        image_path = f"{UPLOAD_FOLDER}/{image_name}"
        with open(image_path, "wb") as image_file:
            try:
                user_agent = generate_desktop_user_agent()
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
                }

                response = requests.get(image_url, headers=headers).content
            except Exception as e:
                print(f"Error: {e}")
                return None
            image_file.write(response)
        return image_path

    @staticmethod
    def save_image_for_short_video(
        image_url,
        target_size=(1080, 1920),
    ):
        image_path = ImageMaker.save_image_url_get_path(image_url)
        image_name = image_path.split("/")[-1]

        video_width, video_height = target_size
        video_ratio = video_width / video_height

        try:
            image = Image.open(image_path)
        except IOError:
            return f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"
        if not (
            image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg")
        ):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        if image.height > image.width:
            crop_height = int(image.width / video_ratio)
            top = (image.height - crop_height) // 2
            bottom = top + crop_height
            image = image.crop((0, top, image.width, bottom))
            image = image.resize(target_size, Image.LANCZOS)
        else:
            new_width = video_width
            new_height = int(image.height * (video_width / image.width))
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            background = Image.new("RGBA", target_size, (0, 0, 0, 255))
            top = (video_height - new_height) // 2
            background.paste(resized_image, (0, top))
            image = background

        if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
            image = image.convert("RGB")

        image.save(image_path)

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        return image_url

    @staticmethod
    def save_image_and_write_text(
        image_url,
        text,
        font_size=50,
        margin=(50, 50, 50, 50),
        text_color=(255, 255, 255),  # Trắng
        stroke_color=(0, 0, 0),  # Màu viền (đen)
        stroke_width=10,  # Độ dày viền
        target_size=(1080, 1350),
    ):
        image_path = ImageMaker.save_image_url_get_path(image_url)
        image_name = image_path.split("/")[-1]

        while not os.path.exists(image_path):
            time.sleep(0.5)

        try:
            image = Image.open(image_path)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}",
            }
        if not (
            image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg")
        ):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        image_width, image_height = target_size
        image_ratio = image_width / image_height

        if image.height > image.width:
            crop_height = int(image.width / image_ratio)
            top = (image.height - crop_height) // 2
            bottom = top + crop_height
            image = image.crop((0, top, image.width, bottom))
            image = image.resize(target_size, Image.LANCZOS)
        else:
            new_width = image_width
            new_height = int(image.height * (image_width / image.width))
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            background = Image.new("RGBA", target_size, (0, 0, 0, 255))
            top = (image_height - new_height) // 2
            background.paste(resized_image, (0, top))
            image = background

        # Resize ảnh về kích thước chuẩn (1080x1080) với chất lượng cao
        image = image.resize(target_size, Image.LANCZOS)

        # Tạo đối tượng vẽ
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(f"{FONT_FOLDER}/dotum.ttc", font_size)
        except IOError:
            print(f"Không tìm thấy font dotum.ttc, sử dụng font mặc định.")
            font = ImageFont.load_default()

        # Tính vùng giới hạn chữ
        left_margin, top_margin, right_margin, bottom_margin = margin
        max_width = image.width - left_margin - right_margin

        # Tự động cắt xuống dòng theo pixel
        lines = wrap_text_by_pixel(draw, text, font, max_width)
        wrapped_text = "\n".join(lines)

        # Vẽ multiline text tại vị trí (left_margin, top_margin)
        draw.multiline_text(
            (left_margin, top_margin),
            wrapped_text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color,
        )

        if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
            image = image.convert("RGB")

        if not (
            image_path.lower().endswith(".jpg")
            or image_path.lower().endswith(".jpeg")
            or image_path.lower().endswith(".webp")
        ):
            image = image.convert("RGB")
            image_name = image_name.rsplit(".", 1)[0] + ".jpg"
            image_path = image_path.rsplit(".", 1)[0] + ".jpg"
        image.save(image_path)

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }
