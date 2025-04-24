#!/bin/bash
watchmedo auto-restart \
    --directory=./ \
    --pattern="*.py" \
    --recursive \
    -- \
    /var/www/toktak/venv/bin/python3 schedule_tasks.py
