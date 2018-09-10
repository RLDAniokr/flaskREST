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

        super(TemperatureSencor, self).__init__()

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

    def get_random_state(self):
        self.value = str(randint(150, 300)) + " люкс"
