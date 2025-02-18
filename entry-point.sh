#!/bin/bash

source /var/www/toktak/venv/bin/activate

gunicorn -w 2 -b 0.0.0.0:8890 "main:app" --log-level debug