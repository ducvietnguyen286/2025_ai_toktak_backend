import os
import datetime
from logging import handlers
import logging
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

    logger.addHandler(handler)

    return logger


def create_error_logger():
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
    )

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)  # Đặt mức độ log là ERROR

    # File handler cho log lỗi
    now_date = datetime.datetime.now()
    filename = now_date.strftime("%d-%m-%Y")
    errorLogHandler = handlers.RotatingFileHandler(
        f"logs/error-paddleocr-{filename}.log",
        backupCount=14,
        encoding="utf-8",
    )
    errorLogHandler.setLevel(logging.ERROR)
    errorLogHandler.setFormatter(formatter)

    # Thêm các handler vào logger
    logger.addHandler(errorLogHandler)

    return logger


MODEL_DIR = os.path.join(os.getcwd(), "app/ais/models/paddleocr_models")
det_model_dir = os.path.join(MODEL_DIR, "det/Multilingual_PP-OCRv3_det_infer")
rec_model_dir = os.path.join(MODEL_DIR, "rec/korean_PP-OCRv3_rec_infer")

app = FastAPI()


def initialize_ocr_model():
    logger = create_logger()
    error_logger = create_error_logger()
    try:
        logger.info("Initializing PaddleOCR...")
        ocr = PaddleOCR(
            use_gpu=True,
            lang="korean",
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
        )
        logger.info("PaddleOCR initialized successfully.")
        return ocr
    except Exception as e:
        error_logger.error(f"Error initializing PaddleOCR: {e}")
        raise


@app.post("/check_text")
async def check_text(request: Request):
    logger = create_logger()
    error_logger = create_error_logger()
    ocr = initialize_ocr_model()
    try:
        data = await request.json()
        image_path = data["image_path"]
        result = ocr.ocr(image_path)
        logger.info(f"Result: {result}")
        texts = [line[1][0] for line in result]
        logger.info(f"Extracted texts: {texts}")
        full_text = " ".join(texts)
        return {"text": full_text}
    except Exception as e:
        error_logger.error(f"Error during OCR processing: {e}")
        return {"error": str(e)}
