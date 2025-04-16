import os
import datetime
from logging import handlers
import logging
from fastapi import FastAPI, Request
from paddleocr import PaddleOCR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)

os.makedirs("logs", exist_ok=True)
now_date = datetime.datetime.now()
filename = now_date.strftime("%d-%m-%Y")

handler = handlers.TimedRotatingFileHandler(
    "logs/paddleocr-{0}.log".format(filename),
    when="midnight",
    interval=1,
    backupCount=14,
    encoding="utf-8",
)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)

errorLogHandler = handlers.RotatingFileHandler(
    "logs/paddleocr-error-{0}.log".format(filename), backupCount=14, encoding="utf-8"
)
errorLogHandler.setLevel(logging.ERROR)
errorLogHandler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(errorLogHandler)

MODEL_DIR = os.path.join(os.getcwd(), "app/ais/models/paddleocr_models")
det_model_dir = os.path.join(MODEL_DIR, "det/Multilingual_PP-OCRv3_det_infer")
rec_model_dir = os.path.join(MODEL_DIR, "rec/korean_PP-OCRv3_rec_infer")

app = FastAPI()

try:
    logger.info("Initializing PaddleOCR...")
    ocr = PaddleOCR(
        use_gpu=True,
        lang="korean",
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
    )
    logger.info("PaddleOCR initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing PaddleOCR: {e}")
    raise


@app.post("/check_text")
async def check_text(request: Request):
    try:
        logger.info("Step 1: Received request")
        data = await request.json()
        image_path = data["image_path"]
        logger.info(f"Step 2: Image path: {image_path}")

        logger.info("Step 3: Running OCR")
        result = ocr.ocr(image_path)
        logger.info(f"Step 4: OCR result: {result}")

        text = "".join([item[1] for item in result]).strip()
        logger.info(f"Step 5: Extracted text: {text}")

        return {"text": text}
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        return {"error": str(e)}
