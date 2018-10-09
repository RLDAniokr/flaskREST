#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
from time import time

import logging

log = logging.getLogger(__name__)


class Device(object):
    """ Родительский класс устройств """
    def __init__(self):
        self.last_response = time()

    def get_info(self):
        response = {
            'dvc_id': self.device_id,
            'dvc_type': self.type,
            'group_name': self.group_name,
            'name': self.name
        }
        return response


class Relay(Device):
    """ Класс реле """
    def __init__(self, dvc_id, group_name, name, ch0name, ch1name, last_val):
        self.device_id = dvc_id
        self.group_name = group_name
        self.name = name

        self.type = 'Relay'
        super(Relay, self).__init__()

        self.ch0name = ch0name
        self.ch1name = ch1name

        if last_val == None:
            self.ch0val = False
            self.ch1val = False
        else:
            self.ch0val = (last_val & 1) == 1
            self.ch1val = ((last_val >> 1) & 1) == 1
            log.info('RELAY %s: RESTORED VALS: %s, %s' %(self.name, self.ch0val, self.ch1val))

    def get_info(self):
        response = {
            'dvc_id': self.device_id,
            'dvc_type': self.type,
            'group_name': self.group_name,
            'name': self.name,
            'ch0name': self.ch0name,
            'ch1name': self.ch1name
        }
        return response


    def sendCmd(self):
        __result_val = ((1 if ch1val else 0) << 1) + (1 if ch0val else 0)

    def update(self, income_array):
        pass
