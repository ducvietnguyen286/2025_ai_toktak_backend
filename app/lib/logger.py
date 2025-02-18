import logging
import datetime
import logging.handlers as handlers

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s: %(message)s',
                              datefmt='%d-%m-%Y %H:%M:%S')

now_date = datetime.datetime.now()
filename = now_date.strftime("%d-%m-%Y")

handler = handlers.TimedRotatingFileHandler('logs/crawler-{0}.log'.format(filename), when='midnight', interval=1, backupCount=14,
                                            encoding='utf-8')
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)

errorLogHandler = handlers.RotatingFileHandler('logs/error-{0}.log'.format(filename), backupCount=14)
errorLogHandler.setLevel(logging.ERROR)
errorLogHandler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(errorLogHandler)
