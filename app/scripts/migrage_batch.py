import json
import os
from app.extensions import db
from app.models.batch import Batch


def import_batch_data(app):
    with app.app_context():
        print("Start Script...")
        json_path = os.path.join(
            os.path.dirname(__file__), "data_scripts", "toktak.image_templates.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                inserts = []
                checked_ids = set()
                for item in data:
                    pass
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error: {e}")
