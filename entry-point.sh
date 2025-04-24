#!/bin/bash

source /var/www/toktak/venv/bin/activate

gunicorn -w 2 -k gevent -b 0.0.0.0:8890 "main:app" --timeout 120 --log-level debug