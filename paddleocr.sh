#!/bin/bash

source /var/www/toktak/paddleocr-venv/bin/activate

gunicorn ocr:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001 --timeout 120 --log-level debug