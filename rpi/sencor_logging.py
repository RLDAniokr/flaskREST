from time import mktime, strptime
from datetime import datetime

import logging
from logging.handlers import TimedRotatingFileHandler

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.propagate = False

format = '%(asctime)s,%(message)s'
FORMATTER = logging.Formatter(format, datefmt='%Y-%m-%d %H:%M:%S')

PATH = './logs/sencor_logs/sencors.csv'
trot_handler = TimedRotatingFileHandler(PATH,
                                        when="D",
                                        interval=1,
                                        backupCount=7)

trot_handler.setFormatter(FORMATTER)
log.addHandler(trot_handler)


class Warden(object):
    def __init__(self, update_fb_fn):
        self.update_fb_fn = update_fb_fn

    def parse_n_write(self, snc_id, snc_type, snc_val, snc_time):
        __acceptable_types = ["Water"]
        if snc_type in __acceptable_types:
            __splitted_val = snc_val.split(" ")
            if len(__splitted_val) == 0:
                return
            else:
                __fmt_val = __splitted_val[0]

            _row = str(snc_id) + "," + __fmt_val
            log.info(_row)

    def stream_handler(self, message):
        pass

    def find_day(self, date, id):
        pass

    def calculate_results(self, df):
        pass

    def pack_results(self, df):
        pass
