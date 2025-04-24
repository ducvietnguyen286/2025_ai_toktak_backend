import os
import traceback
import cv2
import datetime
from logging import handlers
import logging
import numpy as np
from fastapi import FastAPI, Request
from paddleocr import PaddleOCR
from shapely.geometry import Polygon
from shapely.ops import unary_union


def create_logger():
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
    )

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)  # Đặt mức độ log là INFO

    # File handler cho log thông thường
    now_date = datetime.datetime.now()
    filename = now_date.strftime("%d-%m-%Y")
    handler = handlers.TimedRotatingFileHandler(
        f"logs/paddleocr-{filename}.log",
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    # File handler cho log lỗi
    errorLogHandler = handlers.RotatingFileHandler(
        f"logs/error-paddleocr-{filename}.log",
        backupCount=14,
        encoding="utf-8",
    )
    errorLogHandler.setLevel(logging.ERROR)
    errorLogHandler.setFormatter(formatter)

    # Thêm các handler vào logger
    logger.addHandler(handler)
    logger.addHandler(errorLogHandler)

    return logger


logger = create_logger()


MODEL_DIR = os.path.join(os.getcwd(), "app/ais/models/paddleocr_models")
det_model_dir = os.path.join(MODEL_DIR, "det/Multilingual_PP-OCRv3_det_infer")
rec_model_dir = os.path.join(MODEL_DIR, "rec/korean_PP-OCRv3_rec_infer")

app = FastAPI()


try:
    ocr = PaddleOCR(
        use_angle_cls=True,
        use_gpu=True,
        lang="korean",
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
        det_db_unclip_ratio=2.0,
        use_tensorrt=True,
        trt_precision_mode="fp16",
        # Bạn có thể điều chỉnh thêm các tham số sau tùy thuộc vào yêu cầu và phiên bản:
        # trt_max_batch_size=1,
        # trt_workspace_size=1 << 20,
    )
    logger.info("PaddleOCR model initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing PaddleOCR: {e}")
    raise


def merge_close_polygons(polygons, distance_threshold):
    merged = []
    used = [False] * len(polygons)

    for i, poly1 in enumerate(polygons):
        if used[i]:
            continue
        group = [poly1]
        used[i] = True
        for j, poly2 in enumerate(polygons):
            if not used[j] and poly1.distance(poly2) < distance_threshold:
                group.append(poly2)
                used[j] = True
        merged.append(unary_union(group))
    return merged


@app.post("/check_text")
async def check_text(request: Request):
    try:
        data = await request.json()
        image_path = data["image_path"]

        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot read image from path: {image_path}")
            return {"text": "", "ratio": 0}

        result = ocr.ocr(image_path, cls=True)

        height, width = img.shape[:2]
        total_area = width * height

        sum_text_area = 0
        texts = []
        polygons = []
        padding = 10

        if result is None:
            logger.error("No text detected in the image.")
            return {"text": "", "ratio": 0}

        for line_group in result:
            if not line_group or len(line_group) < 1:
                continue

            for line in line_group:
                if len(line) < 2 or (len(line) >= 2 and len(line[0]) < 4):
                    continue

                detection = line[0]
                pts = np.array(detection, dtype=np.int32)

                x_min = max(np.min(pts[:, 0]) - padding, 0)
                y_min = max(np.min(pts[:, 1]) - padding, 0)
                x_max = min(np.max(pts[:, 0]) + padding, width)
                y_max = min(np.max(pts[:, 1]) + padding, height)

                expanded_poly = Polygon(
                    [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
                )
                if not expanded_poly.is_valid:
                    expanded_poly = expanded_poly.buffer(0)
                if expanded_poly.area > 0:
                    polygons.append(expanded_poly)

                texts.append(line[1][0])

        if len(polygons) > 0:
            merged_polygons = merge_close_polygons(polygons, distance_threshold=10)
            sum_text_area = sum(poly.area for poly in merged_polygons)

        if not texts:
            return {"text": "", "ratio": 0}
        full_text = " ".join(texts)
        ratio = sum_text_area / total_area
        return {"text": full_text, "ratio": ratio}
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during OCR processing: {e}")
        return {"text": "", "ratio": 0}
