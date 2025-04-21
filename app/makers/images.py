from concurrent.futures import ThreadPoolExecutor
import io
import os
import time
import datetime
import traceback
from urllib.parse import urlparse
import uuid
import pillow_avif
from PIL import Image, ImageDraw, ImageFont
import requests
import cv2
from ultralytics import YOLO, FastSAM
from google.cloud import vision
import torch
import easyocr
from multiprocessing import Pool
import numpy as np
from app.lib.logger import logger

from app.lib.header import generate_desktop_user_agent

torch.autograd.set_detect_anomaly(True)


date_create = datetime.datetime.now().strftime("%Y_%m_%d")
UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FONT_FOLDER = os.path.join(os.getcwd(), "app/makers/fonts")
CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

PADDLE_OCR_URL = os.environ.get("PADDLE_OCR_URL")
PADDLE_URL = f"{PADDLE_OCR_URL}/check_text"


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


def process_beauty_image(image_path):
    extension = image_path.split(".")[-1].lower()
    if extension == "gif":
        return image_path

    text = ""
    response = requests.post(PADDLE_URL, json={"image_path": image_path})
    if response.status_code == 200:
        result = response.json()
        text = result["text"] or ""
    if len(text) > 50:
        os.remove(image_path)
        return ""
    return image_path


class ImageMaker:

    @staticmethod
    def save_normal_images(images, batch_id=0):
        downloaded_images = []
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_image = {
                executor.submit(
                    ImageMaker.save_image_url_get_path, image_url, batch_id
                ): image_url
                for image_url in images
            }
            downloaded_images = [future.result() for future in future_to_image]

        return downloaded_images

    @staticmethod
    def get_only_beauty_images(images, batch_id=0):
        output_folder = f"{UPLOAD_FOLDER}/{batch_id}"

        os.makedirs(output_folder, exist_ok=True)

        process_images = []
        base_images = []

        downloaded_images = []
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_image = {
                executor.submit(
                    ImageMaker.save_image_url_get_path, image_url, batch_id
                ): image_url
                for image_url in images
            }
            downloaded_images = [future.result() for future in future_to_image]

        for image_path in downloaded_images:
            if not image_path:
                continue
            try:
                image = Image.open(image_path)
            except IOError:
                print(f"Cannot identify image file {image_path}")
                base_images.append(image_path)
                continue

            image_width, image_height = image.size

            if image_height <= (image_width * 4):
                extension = image_path.split(".")[-1].lower()
                if extension == "gif":
                    process_images.append(image_path)
                    continue

                image_cv = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

                if not image_path.lower().endswith(".jpg"):
                    new_image_path = image_path.rsplit(".", 1)[0] + ".jpg"
                    cv2.imwrite(
                        new_image_path, image_cv, [cv2.IMWRITE_JPEG_QUALITY, 90]
                    )
                    image.close()
                    os.remove(image_path)
                    image_path = new_image_path
                else:
                    cv2.imwrite(image_path, image_cv, [cv2.IMWRITE_JPEG_QUALITY, 90])

                process_images.append(image_path)
            else:
                base_images.append(image_path)

            image.close()

        with Pool(processes=5) as pool:
            results = pool.map(process_beauty_image, process_images)

        processed_images = [result for result in results if result]

        cleared_images = []
        for image_path in processed_images:
            if image_path != "":
                cleared_images.append(image_path)

        cleared_images.extend(base_images)

        return cleared_images

    @staticmethod
    def cut_out_long_height_images_by_sam(image_path, batch_id=0):
        logger.info(f"Cut out long height images: {image_path}")
        extension = image_path.split(".")[-1].lower()
        if extension == "gif":
            return [image_path]
        output_folder = f"{UPLOAD_FOLDER}/{batch_id}"

        while not os.path.exists(image_path):
            time.sleep(0.5)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            image = Image.open(image_path)
        except IOError:
            logger.error(f"Cannot identify image file {image_path}")
            print(f"Cannot identify image file {image_path}")
            image_name = image_path.split("/")[-1]
            image_url = f"{CURRENT_DOMAIN}/{date_create}/{batch_id}/{image_name}"
            return [image_url]

        image_width, image_height = image.size

        print(f"Image size: {image_width}x{image_height}")

        if image_height > (image_width * 4):

            model_path = os.path.join(os.getcwd(), "app/ais/models")
            fast_sam_path = os.path.join(model_path, "FastSAM-x.pt")
            yolo_path = os.path.join(model_path, "yolov8s-seg.pt")

            try:
                is_gpu = torch.cuda.is_available()
                logger.info(f"Is GPU available: {is_gpu}")
                if is_gpu:
                    model = FastSAM(fast_sam_path).cuda()
                    # model = YOLO(yolo_path).cuda()
                else:
                    model = FastSAM(fast_sam_path)
                    # model = YOLO(yolo_path)
                results = model.predict(source=image_path, conf=0.5)
                logger.info(f"Results: {results}")
                # results = model(image_path, conf=0.5)
                image_cv = cv2.imread(image_path)
                if image_cv is None:
                    return [image_path]

                cropped_images = []

                excluded_labels = ["barcode", "qr code", "text", "logo"]

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(
                            int, box.xyxy[0]
                        )  # Lấy tọa độ bounding box

                        label = result.names[int(box.cls[0])]
                        conf = box.conf[0].item()

                        if label.lower() in excluded_labels:
                            continue

                        # Kiểm tra kích thước của bounding box
                        w = x2 - x1
                        h = y2 - y1

                        logger.info(f"Bounding box: {x1}, {y1}, {x2}, {y2}")

                        if w < 100 or h < 100:
                            continue

                        cropped = image_cv[y1:y2, x1:x2]  # Cắt ảnh theo bounding box

                        logger.info(f"Label: {label}, Conf: {conf}")

                        if os.environ.get("USE_OCR") == "true":
                            response = requests.post(
                                PADDLE_URL, json={"image_path": image_path}
                            )
                            text = ""
                            if response.status_code == 200:
                                result = response.json()
                                text = result["text"] or ""
                            if len(text) > 25:
                                continue

                        timestamp = int(time.time())
                        unique_id = uuid.uuid4().hex
                        new_name = f"{timestamp}_{unique_id}.jpg"
                        cropped_path = os.path.join(output_folder, new_name)

                        # Resize the cropped image to the target size (1350x1080)
                        target_size = (1350, 1080)
                        h, w, _ = cropped.shape
                        scale = min(target_size[1] / h, target_size[0] / w)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        resized = cv2.resize(
                            cropped, (new_w, new_h), interpolation=cv2.INTER_AREA
                        )

                        cropped_resized = np.zeros(
                            (target_size[1], target_size[0], 3), dtype=np.uint8
                        )
                        y_offset = (target_size[1] - new_h) // 2
                        x_offset = (target_size[0] - new_w) // 2
                        cropped_resized[
                            y_offset : y_offset + new_h, x_offset : x_offset + new_w
                        ] = resized

                        cv2.imwrite(
                            cropped_path, cropped_resized
                        )  # Save the resized image

                        logger.info(f"Cropped image saved: {cropped_path}")

                        cropped_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{new_name}"

                        cropped_images.append((cropped_url, conf))

                logger.info(f"Cropped images: {cropped_images}")

                if cropped_images:
                    needed_length = 5
                    cropped_data_sorted = sorted(
                        cropped_images, key=lambda x: x[1], reverse=True
                    )
                    top = [url for url, c in cropped_data_sorted[:needed_length]]
                    for cropped_url, _ in cropped_images[needed_length:]:
                        cropped_image_path = os.path.join(
                            output_folder, os.path.basename(cropped_url)
                        )
                        if os.path.exists(cropped_image_path):
                            os.remove(cropped_image_path)
                    image.close()
                    os.remove(image_path)
                    return top

            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Error: {e}")
                traceback.print_exc()
                image_name = image_path.split("/")[-1]
                image_url = (
                    f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"
                )
                return [image_url]

        image_name = image_path.split("/")[-1]
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"
        return [image_url]

    @staticmethod
    def cut_out_long_height_images_by_google(image_url, batch_id=0):
        image_path = ImageMaker.save_image_url_get_path(image_url, batch_id=batch_id)
        output_folder = f"{UPLOAD_FOLDER}/{batch_id}"
        print(f"Cut out long height images: {image_path}")

        while not os.path.exists(image_path):
            time.sleep(0.5)

        try:
            image = Image.open(image_path)
            image = image.convert("RGB")
            image.save(image_path)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            image_name = image_path.split("/")[-1]
            image_url = f"{CURRENT_DOMAIN}/{date_create}/{batch_id}/{image_name}"
            return [image_url]

        image_width, image_height = image.size

        print(f"Image size: {image_width}x{image_height}")

        if image_height > (image_width * 2):
            try:
                key_path = os.path.join(os.getcwd(), "google-cloud-vision.json")
                client = vision.ImageAnnotatorClient.from_service_account_file(key_path)
                with io.open(image_path, "rb") as image_file:
                    content = image_file.read()

                image = vision.Image(content=content)
                response = client.object_localization(image=image)

                excluded_labels = ["Barcode", "QR code", "Text", "Logo"]

                print(
                    f"Found {len(response.localized_object_annotations)} objects in image"
                )

                original_image = Image.open(image_path)
                cropped_images = []
                for idx, obj in enumerate(response.localized_object_annotations):
                    name = obj.name

                    print(f"Object {image_path}: {name}")

                    if name in excluded_labels:
                        continue

                    vertices = [
                        (
                            int(vertex.x * original_image.width),
                            int(vertex.y * original_image.height),
                        )
                        for vertex in obj.bounding_poly.normalized_vertices
                    ]

                    x1, y1 = vertices[0]
                    x2, y2 = vertices[2]
                    cropped_image = original_image.crop((x1, y1, x2, y2))
                    cropped_resized = cropped_image.resize((640, 640), Image.LANCZOS)
                    timestamp = int(time.time())
                    unique_id = uuid.uuid4().hex
                    new_name = f"{timestamp}_{unique_id}.jpg"
                    output_path = os.path.join(output_folder, new_name)
                    cropped_resized.save(output_path)

                    cropped_url = (
                        f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{new_name}"
                    )
                    cropped_images.append(cropped_url)
                if cropped_images:
                    os.remove(image_path)
                    return cropped_images

            except Exception as e:
                print(f"Error: {e}")
                image_name = image_path.split("/")[-1]
                image_url = (
                    f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"
                )
                return [image_url]

        image_name = image_path.split("/")[-1]
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"
        return [image_url]

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
        batch_id=0,
        margin=(90, 50, 90, 160),
        text_color=(0, 0, 0),  # Trắng
        stroke_color=(255, 255, 255),  # Màu viền (đen)
        stroke_width=10,  # Độ dày viền
        target_size=(1080, 1350),
        is_avif=False,
    ):

        image_path = ImageMaker.save_image_url_get_path(image_url, batch_id, is_avif)
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
            font = ImageFont.truetype(f"{FONT_FOLDER}/CookieRun-Bold.ttf", font_size)
        except IOError:
            print(f"Không tìm thấy font CookieRun-Bold.ttf, sử dụng font mặc định.")
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
        # Tính toán vị trí text_x để căn giữa theo chiều ngang
        text_x = (image.width - text_width) // 2

        # Vẽ multiline text tại vị trí (left_margin, top_margin)
        draw.multiline_text(
            (text_x, text_y),
            wrapped_text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color,
            align="center",
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

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

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
        batch_id=0,
        target_size=(1080, 1350),
        is_avif=False,
    ):
        image_path = ImageMaker.make_resize_image(
            first_image, target_size, batch_id, is_avif
        )
        image_name = image_path.split("/")[-1]
        try:
            background = cv2.imread(image_path)
            overlay = background.copy()
            overlay[:] = (0, 0, 0)  # Màu đen
            alpha = 0.2  # Độ mờ (opacity)
            background = cv2.addWeighted(overlay, alpha, background, 1 - alpha, 0)
        except IOError:
            print(f"Cannot identify image file {image_path}")
            file_size = os.path.getsize(image_path)
            mime_type = "image/jpeg"
            return {
                "file_size": file_size,
                "mime_type": mime_type,
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}",
            }
        background_pil = Image.fromarray(cv2.cvtColor(background, cv2.COLOR_BGR2RGB))
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
            bottom_margin=260,
        )
        image.save(image_path)
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

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
        batch_id=0,
        target_size=(1080, 1350),
        is_avif=False,
    ):
        image_path = ImageMaker.make_resize_image(
            first_image, target_size, batch_id, is_avif
        )
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
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}",
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
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

        file_size = os.path.getsize(image_path)
        mime_type = "image/jpeg"

        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "image_url": image_url,
        }

    @staticmethod
    def make_resize_image(image, target_size, batch_id=0, is_avif=False):
        image_path = ImageMaker.save_image_url_get_path(image, batch_id, is_avif)
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
                "image_url": f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}",
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
        batch_id=0,
        target_size=(1080, 1350),
    ):
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        image_name = f"{timestamp}_{unique_id}.jpg"

        os.makedirs(f"{UPLOAD_FOLDER}/{batch_id}", exist_ok=True)

        image_path = f"{UPLOAD_FOLDER}/{batch_id}/{image_name}"
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
        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

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
            print(f"Không tìm thấy font {font_path}, sử dụng font mặc định.")
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
        line_spacing = 80  # Khoảng cách giữa các dòng
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
            text_y += line_spacing + 80  # Khoảng cách giữa các dòng

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
            print(f"Không tìm thấy font {font_path}, sử dụng font mặc định.")
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
    def save_image_url_get_path(image_url, batch_id=0, is_avif=False):
        new_folder = f"{UPLOAD_FOLDER}/{batch_id}"
        os.makedirs(new_folder, exist_ok=True)
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

        temp_image = ""
        if is_avif:
            temp_image = f"{timestamp}_{unique_id}.avif"
        image_name = f"{timestamp}_{unique_id}.{image_ext}"

        image_path = f"{new_folder}/{image_name}"
        image_temp_path = f"{new_folder}/{temp_image}"
        if not is_avif:
            with open(image_path, "wb") as image_file:
                response = ImageMaker.request_content_image(image_url)
                image_file.write(response)
        else:
            with open(image_temp_path, "wb") as temp_avif:
                response = ImageMaker.request_content_image(image_url)
                temp_avif.write(response)

            with Image.open(image_temp_path) as temp_image:
                temp_image = temp_image.convert("RGB")
                temp_image.save(image_path, "JPEG", quality=90, optimize=True)

            time.sleep(0.1)
            os.remove(image_temp_path)
        return image_path

    @staticmethod
    def request_content_image(image_url):
        try:
            user_agent = generate_desktop_user_agent()
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            }

            response = requests.get(image_url, headers=headers).content
            return response
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def save_image_for_short_video(
        image_url, batch_id=0, target_size=(1080, 1920), is_avif=False
    ):
        image_path = ImageMaker.save_image_url_get_path(image_url, batch_id, is_avif)
        image_name = image_path.split("/")[-1]

        video_width, video_height = target_size
        video_ratio = video_width / video_height

        try:
            image = Image.open(image_path)
        except IOError:
            return f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

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
            image = image.convert("RGB")

        image.save(image_path)

        image_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{image_name}"

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
