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

    def check_timeout(self):
        if (time() - self.last_response >= self.timeout):
            self.value = "Таймаут"
            return True
        else:
            return False


class TemperatureSencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Temperature'

        self.timeout = 1080

        super(TemperatureSencor, self).__init__()

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        self.last_response = time()

        __data_lb = income_array[5]
        __data_sb = income_array[6] << 8

        __data_sum = (__data_lb | __data_sb) & 0xFFF

        if __data_sum in [0xFF]:
            self.value = "Ошибка датчика"
        else:
            self.value = str(__data_sum/10.00) + " °C"

    def get_random_state(self):
        self.value = str(randint(15, 30)) + " °C"


class HumiditySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Humidity'

        self.timeout = 1080

        super(HumiditySencor, self).__init__()

    def convert_data(self, income_array):
        # TBD
        pass

    def get_random_state(self):
        self.value = str(randint(35, 50)) + " %"


class LuminositySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Luminosity'

        self.timeout = 1080

        super(LuminositySencor, self).__init__()

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        self.last_response = time()

        __data_lb = income_array[5]
        __data_sb = income_array[6] << 8

        __data_sum = (__data_lb | __data_sb)

        if __data_sum in [0xFF]:
            self.value = "Ошибка датчика"
        else:
            self.value = str(__data_sum) + " люкс"

    def get_random_state(self):
        self.value = str(randint(150, 300)) + " люкс"


class DoorSencor(Sencor):
    """ Класс датчиков открытия двери """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Door'

        self.timeout = 1080

        super(DoorSencor, self).__init__()

    def convert_data(self, data):
        self.last_response = time()

        __data_lb = data[7]

        if __data_lb in [0xFF]:
            self.value = "Ошибка датчика"
        else:
            self.value = "Закрыто" if __data_lb == 0 else "Открыто"


class PulseSencor(Sencor):
    """ Класс счетчиков импульсов """
    def __init__(self, snc_id, group_name, name):
        self.sencor_id = snc_id
        self.group_name = group_name
        self.name = name
        self.type = 'Pulse'

        self.timeout = 3605

        super(PulseSencor, self).__init__()

        self.prev_pulses = 0
        self.pow = 0.0
        self.kwt = 0.0


    def convert_data(self, data):
        """
            Конвертация принятых данных
        """
        # Power calculate
        # Hago geJluTb Ha npoIIIegIIIuu' nepuog BpeMeHu
        self.period_pwr = (time() - self.last_response)/60
        self.last_response = time()

        __pulses = 0
        try:
            for i in range(0, 4):
                __tmp = data[5+i] << (8*i)
                __pulses = __pulses | __tmp
        except Exception:
                log.warn("Cant calc total pulses in Pulse:%s" % self.sencor_id)
                log.info("Data length: %s" % len(data))
                return
        finally:
            self.kwt = " %.2f КВт/ч" % (__pulses/3200.00)
            log.info("kwt: %s" % self.kwt)

            if self.prev_pulses != 0:
                self.pow = str((__pulses - self.prev_pulses) * 1.125 / self.period_pwr) + " Вт"
            else:
                self.pow = "0 Вт"
            log.info("pow: %s" % self.pow)
