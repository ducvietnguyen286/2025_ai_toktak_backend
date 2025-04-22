import os
import cv2
import datetime
from logging import handlers
import logging
import numpy as np
from fastapi import FastAPI, Request
from paddleocr import PaddleOCR


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


MODEL_DIR = os.path.join(os.getcwd(), "app/ais/models/paddleocr_models")
det_model_dir = os.path.join(MODEL_DIR, "det/Multilingual_PP-OCRv3_det_infer")
rec_model_dir = os.path.join(MODEL_DIR, "rec/korean_PP-OCRv3_rec_infer")

app = FastAPI()


def initialize_ocr_model():
    logger = create_logger()
    try:
        logger.info("Initializing PaddleOCR...")
        ocr = PaddleOCR(
            use_angle_cls=True,
            use_gpu=True,
            lang="korean",
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
        )
        logger.info("PaddleOCR initialized successfully.")
        return ocr
    except Exception as e:
        logger.error(f"Error initializing PaddleOCR: {e}")
        raise


@app.post("/check_text")
async def check_text(request: Request):
    logger = create_logger()
    ocr = initialize_ocr_model()
    try:
        data = await request.json()
        image_path = data["image_path"]

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Không thể đọc ảnh từ đường dẫn được cung cấp!")

        result = ocr.ocr(image_path, cls=True)

        height, width = img.shape[:2]
        total_area = width * height

        sum_text_area = 0
        texts = []
        for line_group in result:
            for line in line_group:
                detection = line[0]
                x_coords = [pt[0] for pt in detection]
                y_coords = [pt[1] for pt in detection]

                box_width = max(x_coords) - min(x_coords)
                box_height = max(y_coords) - min(y_coords)
                box_area = box_width * box_height
                sum_text_area += box_area

                texts.append(line[1][0])

        if not texts:
            return {"text": ""}
        logger.info(f"Extracted texts: {texts}")
        logger.info(f"sum_text_area: {sum_text_area}")
        full_text = " ".join(texts)
        ratio = sum_text_area / total_area
        return {"text": full_text, "ratio": ratio}
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        return {"error": str(e)}
