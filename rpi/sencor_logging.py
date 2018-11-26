from time import mktime, strptime, time
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


def timeit(fun):
    def timed(*args, **kwargs):
        ts = time.time()
        result = fun(*args, **kwargs)
        te = time.time()
        td = te-ts

        LOG.info('%r : %2.2f sec' % (fun.__name__, td))
        return result

    return timed


class Warden(object):
    def __init__(self, update_fb_fn, read_fb_fn):
        self.update_fb_fn = update_fb_fn
        self.read_fb_fn = read_fb_fn
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
        __data = message["data"]
        LOG.info("FROM STATS - DATA: %s" % (__data))

        if not __data:
            return

        if ('status' in __data):
            if __data['status'] == "AWAIT":
                return

            elif __data['status'] == "PENDING":
                if ('date' in __data) and ('id' in __data):
                    LOG.info("CALCA")
                    _date = __data['date']
                    _id = int(__data['id'])
                    self.send_stats(_date, _id)
                else:
                    __stats_params = self.read_fb_fn()
                    __have_id = __stats_params['id'] != "None"
                    __have_date = __stats_params['date'] != "None"
                    if __have_id and __have_date:
                        _date = __stats_params['date']
                        _id = int(__stats_params['id'])
                        self.send_stats(_date, _id)

            elif __data['status'] == "FAIL":
                self.cancel = True

    @timeit
    def send_stats(self, date, id):
        # TODO: Get local tz from system
        __tz = 'Europe/Moscow'
        __path = PATH
        __today = datetime.today().strftime('%Y-%m-%d')
        if date != __today:
            __path += ('.' + date)
        try:
            LOG.info(__today)
            __df = pd.read_csv(__path, names=['date', 'id', 'value'], sep=',')
            __df['date'] = pd.to_datetime(__df['date']).dt.tz_localize(__tz)
            __df.set_index('date', inplace=True)
        except FileNotFoundError:
            self.update_fb_fn(status="404")
            return

        if self.cancel:
            return

        try:
            __calc_df = self.calculate_results(__df, id)
            if self.cancel:
                return

            _output = self.pack_results(__calc_df)
            if self.cancel:
                return

            self.update_fb_fn(status="OK", data=_output)
        except Exception as e:
            LOG.exception(e)
            self.update_fb_fn(status="FAIL")

    def calculate_results(self, df, snc_id):
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
        _output_dict = {}
        for index, row in df.iterrows():
            if pd.isna(row['max']):
                row['max'] = '-'
            if pd.isna(row['diff']):
                row['diff'] = '-'
            _hour = index.hour
            _output_dict[str(_hour) + "/max"] = row['max']
            _output_dict[str(_hour) + "/diff"] = row['diff']

        LOG.critical(_output_dict)

        return _output_dict
