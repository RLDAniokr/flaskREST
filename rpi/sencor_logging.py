from time import mktime, strptime
from datetime import datetime
import pandas as pd

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

# TEMP: NOTE: XXX: separate log
LOG = logging.getLogger("Warden")
LOG.setLevel(logging.INFO)


class Warden(object):
    def __init__(self, update_fb_fn):
        self.update_fb_fn = update_fb_fn
        self.cancel = False

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
        LOG.info("GOT MSG")
        self.cancel = False
        __from = message["path"]
        __data = message["data"]
        LOG.info("FROM: %s DATA: %s" % (__from, __data))

        if ('status' in __data):
            if __data['status'] == "AWAIT":
                return

        if ('date' in __data) and ('id' in __data):
            _date = __data['date']
            _snc_id = int(__data['id'])
            self.send_stats(_date, _id)
        elif __data['status'] == "FAIL":
            LOG.critical("MOBILE IS TIRED")
            self.cancel = True
        else:
            self.update_fb_fn(status="FAIL")

    def send_stats(self, date, id):
        # TODO: Get local tz from system
        __tz = 'Europe/Moscow'
        __path = PATH
        __today = datetime.today().strftime('%Y-%m-%d')
        if date != __today:
            __path += ('.' + date)
        try:
            __df = pd.read_csv(__path, names=['date', 'id', 'value'], sep=',')
            __df['date'] = pd.to_datetime(df['date']).dt.tz_localize(__tz)
            __df.set_index('date', inplace=True)
        except FileNotFoundError:
            self.update_fb_fn(status="404")
            return

        if self.cancel:
            return

        try:
            __calc_df = self.calculate_results(__df)
            if self.cancel:
                return

            _output = self.pack_results(__calc_df)
            if self.cancel:
                return

            self.update_fb_fn(status="OK", data=_output)
        except Exception as e:
            LOG.exception(e)
            self.update_fb_fn(status="FAIL")

    def calculate_results(self, df):
        # Slice given sencor
        __snc_rows = df[(df.id == snc_id)]
        # Resample frame by hours & get maximal values
        _out_df = pd.DataFrame()
        # Get maximals
        _out_df['max'] = __snc_rows.resample('H')['value'].max()
        # Get differences of maximals
        _out_df['diff'] = _out_df['max'].diff()
        return _out_df

    def pack_results(self, df):
        # TODO: change index name for more convinient one
        df.index = [i for i in range(0, len(df))]

        _output_dict = {}
        for index, row in df.iterrows():
            if pd.isna(row['max']):
                row['max'] = '-'
            if pd.isna(row['diff']):
                row['diff'] = '-'
            _output_dict[str(index) + "/max"] = row['max']
            _output_dict[str(index) + "/diff"] = row['diff']

        return _output_dict
