#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
import logging

log = logging.getLogger(__name__)

class Device(object):
    """ Родительский класс устройств """
    def __init__(self):
        self.value = ''
        #self.last_response = time()

class Relay(Device):
    """ Класс реле """
    def __init__(self, id, group_name, name):
        self.sencor_id = id
        self.group_name = group_name
        self.name = name

        super(Relay, self).__init__()

        self.value = 'false'

    def switch_value(self):
        self.value = 'true' if self.value == 'false' else 'false'
