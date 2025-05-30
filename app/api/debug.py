# coding: utf8
import time
from flask_restx import Namespace, Resource
from gevent import util

ns = Namespace(name="debug", description="User API")
from gevent import sleep


@ns.route("/gurnicorn")
class DebugGunicorn(Resource):
    def get(self):
        start = time.time()
        sleep(0.1)
        end = time.time()

        util.print_run_info()

        return {"elapsed": end - start}
