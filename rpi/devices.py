#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
from time import time

import logging

log = logging.getLogger(__name__)


class Device(object):
    """ Родительский класс устройств """
    def __init__(self):
        self.value = 0
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
    def __init__(self, dvc_id, group_name, name):
        self.device_id = dvc_id
        self.group_name = group_name
        self.name = name

        self.type = 'Relay'
        super(Relay, self).__init__()

        self.value = False

    def switch_value(self):
        #self.value = !self.value
        pass
