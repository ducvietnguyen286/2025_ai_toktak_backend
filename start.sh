#!/bin/bash
set -e

# Kích hoạt virtual environment
source /var/www/2025_ai_toktak_be/venv/bin/activate


# Khởi động Gunicorn với Gevent cho API I/O-bound
exec gunicorn main:application \
  --bind 0.0.0.0:8890 \
  --worker-class gevent \
  --workers 4 \
  --worker-connections 1000 \
  --access-logfile /var/www/logs/toktak_access.log \
  --error-logfile /var/www/logs/toktak_error.log \
  --log-level info \
  --timeout 120
