#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

# Импорт модулей
from time import mktime, strptime, time
from datetime import datetime
import pandas as pd

import logging
from logging.handlers import TimedRotatingFileHandler

# Файловый логгер
log = logging.getLogger(__name__)
# Уровень INFO
log.setLevel(logging.INFO)
# Не передавать себя в родительский лог
log.propagate = False

# Формат сообщений
format = '%(asctime)s,%(message)s'
# Применение фоомата сообщений и даты
FORMATTER = logging.Formatter(format, datefmt='%Y-%m-%d %H:%M:%S')

# Путь к файлу лога
PATH = './logs/sencor_logs/sencors.csv'
# Применение настроек для обработчика
trot_handler = TimedRotatingFileHandler(PATH,
                                        when="D",
                                        interval=1,
                                        backupCount=7)

# Применение формата
trot_handler.setFormatter(FORMATTER)
# Добавление обработчика к файловому логеру
log.addHandler(trot_handler)

# Отдельный логгер, который передается на родительский (основной) лог
# TEMP: NOTE: XXX: separate log
LOG = logging.getLogger("Warden")
LOG.setLevel(logging.INFO)


def timeit(fun):
    """ Декоратор для высчитывания времени выполнения функции """
    def timed(*args, **kwargs):
        # Время начала выполнения
        ts = time()
        # Выполнение измеряемой функции
        result = fun(*args, **kwargs)
        # Время конца выполнения функци
        te = time()
        # Разница времени
        td = te-ts

        # Вывод времени в лог (основной)
        LOG.info('%r : %2.2f sec' % (fun.__name__, td))
        # Возвращение результата выполнения замеряемой функции
        return result

    # Вернуть результат выполнения внутренней функции
    return timed


class Warden(object):
    """ Класс логгера для данных датчиков (с чтением+выборкой) """
    def __init__(self, update_fb_fn, read_fb_fn):
        # Метод обновления данных в облачной БД
        self.update_fb_fn = update_fb_fn
        # Метод чтения данных из облачной БД
        self.read_fb_fn = read_fb_fn
        # Флаг отмены запроса
        self.cancel = False

    def parse_n_write(self, snc_id, snc_type, snc_val, snc_time):
        """ Метод конкатенации данных и записи в файл """
        # Преемлемые типы датчиков
        __acceptable_types = ["Water"]
        # Если тип датчика подходит
        if snc_type in __acceptable_types:
            # Выделить числовой показатель по разделителю пробела
            __splitted_val = snc_val.split(" ")
            # Если пробела нет, то данные - "ошибка" или "таймаут"
            if len(__splitted_val) == 0:
                # Не записывать и вернуться
                return
            else:
                # Забрать числовой показатель
                __fmt_val = __splitted_val[0]

            # Конкатенация строки
            _row = str(snc_id) + "," + __fmt_val
            # Запись в файл
            log.info(_row)

    def stream_handler(self, message):
        """ Обработчик команд статистики """
        LOG.info("GOT MSG")
        # Сбросить флаг отмены при новой команде
        self.cancel = False
        # Данные команды
        __data = message["data"]
        LOG.info("FROM STATS - DATA: %s" % (__data))

        # Если данных нет
        if not __data:
            # Вернуться
            return

        # Если в данных имеется изменение статуса
        if ('status' in __data):
            # Не реагировать на статус "Ожидание"
            if __data['status'] == "AWAIT":
                return

            # При статусе "Выполнение"
            elif __data['status'] == "PENDING":
                # Если в данных имеются дата и идентификатор
                if ('date' in __data) and ('id' in __data):
                    # Снять параметры запроса
                    _date = __data['date']
                    _id = int(__data['id'])
                    # Снять статистику и отправить ее
                    self.send_stats(_date, _id)
                # Если данные изменены частично
                else:
                    # Считать параметры из базы
                    __stats_params = self.read_fb_fn()
                    # Флаг наличия идентификатора
                    __have_id = __stats_params['id'] != "None"
                    # Флаг наличия даты
                    __have_date = __stats_params['date'] != "None"
                    # Если имеются и дата и идентификатор
                    if __have_id and __have_date:
                        # Снять параметры запроса
                        _date = __stats_params['date']
                        _id = int(__stats_params['id'])
                        # Снять статистику и отправить ее
                        self.send_stats(_date, _id)

            # Если с телефона пришел статус "Ошибка" (таймаут запроса)
            elif __data['status'] == "FAIL":
                # Установить флаг отмены
                self.cancel = True

    @timeit
    def send_stats(self, date, id):
        """ Метод снятия и отправки статистики """
        # TODO: Get local tz from system
        # Часовой пояс
        __tz = 'Europe/Moscow'
        # Путь к файлу лога
        __path = PATH
        # Сегоняшняя дата
        __today = datetime.today().strftime('%Y-%m-%d')
        # Если дата в запросе не совпадает с сегодняшней
        if date != __today:
            # Добавить суффикс с датой к имени файла
            __path += ('.' + date)
        try:
            # Считать лог-файл и привести его типу pd.DataFrame
            # Установить имена столбцов и тип разделителя
            __df = pd.read_csv(__path, names=['date', 'id', 'value'], sep=',')
            # Установить локальный часовой пояс для даты
            __df['date'] = pd.to_datetime(__df['date']).dt.tz_localize(__tz)
            # Установить поле даты в качестве индексируемого поля
            __df.set_index('date', inplace=True)
        except FileNotFoundError:
            # Если файл не найден
            self.update_fb_fn(status="404")
            return

        # Вернуться при флаге отмены
        if self.cancel:
            return

        try:
            # Высчитать почасовые экстремумы и разницы
            __calc_df = self.calculate_results(__df, id)
            # Вернуться при флаге отмены
            if self.cancel:
                return

            # Сформировать пакет данных для отправки
            _output = self.pack_results(__calc_df)
            # Вернуться при флаге отмены
            if self.cancel:
                return

            # Отправить сформированный пакет данных в облачную базу
            self.update_fb_fn(status="OK", data=_output)
        except Exception as e:
            LOG.exception(e)
            self.update_fb_fn(status="FAIL")

    def calculate_results(self, df, snc_id):
        """ Метод почасового расчета максимумов и разниц показаний датчика """
        # Выделить строки с предоставленным идентификатором
        __snc_rows = df[(df.id == snc_id)]
        # Инициализация выходного DataFrame
        _out_df = pd.DataFrame()
        # Получить максимумы по часам и добавить к выходному DataFrame
        _out_df['max'] = __snc_rows.resample('H')['value'].max()
        # Получить разницы между максимумами близлежащих часов
        _out_df['diff'] = _out_df['max'].diff()
        # Вернуть DataFrame
        return _out_df

    def pack_results(self, df):
        """ Метод формирования пакета для отправки Firebase """
        # Инициализация выходного словаря
        _output_dict = {}
        # Проходка по строкам DataFrame
        # index - время
        # row - максимум и разница соседних максимумов (через ключ)
        for index, row in df.iterrows():
            # Если максимум не является числом
            if pd.isna(row['max']):
                # Заменить его на прочерк
                row['max'] = '-'
            # Если разница не является числом
            if pd.isna(row['diff']):
                # Заменить ее на прочерк
                row['diff'] = '-'
            # Выделить час из индексного поля
            # (пр.: index = 12:00:00 => _hour = 12)
            _hour = index.hour
            # Добавить в выходной словарь значения максимума и разницы
            _output_dict[str(_hour) + "/max"] = row['max']
            _output_dict[str(_hour) + "/diff"] = row['diff']

        # Вывести в главный лог выходной словарь
        LOG.info(_output_dict)

        # Вернуть выходной словарь
        return _output_dict
