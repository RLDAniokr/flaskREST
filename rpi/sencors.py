#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from time import time

# TEMP: # DEBUG: # XXX:
from random import randint

import logging

log = logging.getLogger(__name__)


class Sencor(object):
    """ Родительский класс датчиков """
    def __init__(self):
        self.value = '-'
        self.last_response = time()

    def get_info(self):
        response = {
            'snc_id': self.sencor_id,
            'snc_type': self.type,
            'group_name': self.group_name,
            'name': self.name
        }
        return response


class TemperatureSencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name

        self.type = 'Temperature'
        self.type_id = 0

        super(TemperatureSencor, self).__init__()

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        self.last_responce = time.time()

        log.debug("Testing data conversion")

        __data_lb = income_array[5]
        __data_sb = income_array[6] << 8

        __data_sum = (__data_lb | __data_sb) & 0xFFF

        if __data_sum in [0xFF, 0x00]:
            self.data = "Ошибка датчика"
        else:
            self.data = str(__data_sum/10.00) + " °C"

    def get_random_state(self):
        self.value = str(randint(15, 30)) + " °C"


class HumiditySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Humidity'

        super(HumiditySencor, self).__init__()

    def get_random_state(self):
        self.value = str(randint(35, 50)) + " %"


class LuminositySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Luminosity'

        super(LuminositySencor, self).__init__()

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        self.last_responce = time.time()

        log.debug("Testing data conversion")

        __data_lb = income_array[5]
        __data_sb = income_array[6] << 8

        __data_sum = (__data_lb | __data_sb)

        if __data_sum in [0xFF, 0x00]:
            self.data = "Ошибка датчика"
        else:
            self.data = str(__data_sum) + " люкс"

    def get_random_state(self):
        self.value = str(randint(150, 300)) + " люкс"

class DoorSencor(Sencor):
    """ Класс датчиков открытия двери """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Door'

        super(DoorSencor, self).__init__()

    def convert_data(self, data):
        self.last_responce = time.time()

        __data_lb = data[7]

        if __data_lb in self.settings.error_codes:
            self.data = "Ошибка датчика"
        else:
            self.data = "Открыто" if __data_lb == 0 else "Закрыто"
