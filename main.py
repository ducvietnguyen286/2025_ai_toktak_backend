# coding: utf8
import os

from dotenv import load_dotenv

load_dotenv(override=False)

from app import create_app  # noqa
from app.config import configs as config  # noqa

config_name = os.environ.get('FLASK_CONFIG') or 'develop'
config_app = config[config_name]
application = app = create_app(config_app)

if __name__ == '__main__':
    application.run()
