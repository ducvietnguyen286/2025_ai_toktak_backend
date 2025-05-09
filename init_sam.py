import os
import threading
import traceback
import cv2
import datetime
from logging import handlers
import logging
from fastapi import FastAPI, Request
from ultralytics import FastSAM
import torch

gpu_semaphore = threading.Semaphore(5)

sam_model = None


def init_sam_model():
    global sam_model

    model_path = os.path.join(os.getcwd(), "app/ais/models")
    fast_sam_path = os.path.join(model_path, "FastSAM-x.pt")
    # yolo_path = os.path.join(model_path, "yolov8s-seg.pt")

    if sam_model is None:
        sam_model = FastSAM(fast_sam_path)
    return sam_model


def create_logger():
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
    )

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    now_date = datetime.datetime.now()
    filename = now_date.strftime("%d-%m-%Y")
    handler = handlers.TimedRotatingFileHandler(
        f"logs/sam-{filename}.log",
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    errorLogHandler = handlers.RotatingFileHandler(
        f"logs/error-sam-{filename}.log",
        backupCount=14,
        encoding="utf-8",
    )
    errorLogHandler.setLevel(logging.ERROR)
    errorLogHandler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(errorLogHandler)

    return logger


logger = create_logger()

app = FastAPI()
init_sam_model()


@app.post("/check-beauty-image")
async def check_text(request: Request):
    try:
        data = await request.json()
        image_path = data["image_path"]

        img = cv2.imread(image_path)
        if img is None:
            return {"images": []}
        height, width, _ = img.shape
        if height <= (width * 4):
            return {"images": []}
        device = "cuda" if torch.cuda.is_available() else "cpu"
        with gpu_semaphore:
            results = sam_model(
                image_path,
                retina_masks=True,
                imgsz=1024,
                conf=0.6,
                iou=0.9,
                device=device,
            )
            return {"images": results}

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during OCR processing: {e}")
        return {"images": []}
