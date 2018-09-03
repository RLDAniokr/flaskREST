#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

# TODO: import stuff
# import sql
import threading
from time import sleep

from sencors import *
from devices import *

import logging

log = logging.getLogger(__name__)

class rpiHub(object):
    """ Класса хаба Raspberry """
    def __init__(self):
        # TODO: add get sencors from db
        self.snc_list = []
        # TODO: add get devices from db
        self.dvc_list = []
        # TODO: init firebase
        self.init_read_sencors()

    def read_sencors_from_db(self):
        #self.snc_list = sql.get_sencors()
        pass

    def read(self):
        try:
            while(True):
                for snc in self.snc_list:
                    snc.get_random_state()
                    print("Sencor %s:%s" % (snc.name, snc.value))
                    # TODO: send value to firebase
                sleep(5)
        except Exception as e:
            raise

    def init_read_sencors(self):
        self.read_thread = threading.Thread(target=self.read)
        self.read_thread.daemon = True
        self.read_thread.start()

    def add_snc(self, snc_type, snc_id, snc_group, snc_name):
        """ Добавить датчик """
        # TODO: check if already exists
        if snc_type == "temp":
            new_sencor = TemperatureSencor(id=snc_id, group_name=snc_group, name=snc_name)
        elif snc_type == "humi":
            new_sencor = HumiditySencor(id=snc_id, group_name=snc_group, name=snc_name)
        elif snc_type == "lumi":
            new_sencor = LuminositySencor(id=snc_id, group_name=snc_group, name=snc_name)
        else:
            log.error("Unknown sencor type")
            return
        self.snc_list.append(new_sencor)

    def add_dvc(self, dvc_type, dvc_id, dvc_group, dvc_name):
        """ Добавить устройство """
        # TODO: check if already exists
        if dvc_type == 'relay':
            new_device = Relay(id=dvc_id, group_name=dvc_group, name=dvc_name)
        else:
            log.error("Unknown device type")
            return
        self.dvc_list.append(new_device)

    def edit_snc(self):
        """ Редактировать настройки датчика """
        pass

    def edit_dvc(self):
        """ Редактировать настройки устройства """
        pass

    def del_snc(self):
        pass

    def del_dvc(self):
        pass

if __name__ == '__main__':
    testHub = rpiHub()

    testHub.add_snc('temp', 0, 'kitchen', 'kitchen_temp')
    testHub.add_snc('humi', 1, 'kitchen', 'kitchen_humi')
    testHub.add_snc('lumi', 2, 'hall', 'hall_lumi')

    testHub.add_dvc('relay', 3, 'kitchen', 'fridge')
    testHub.add_dvc('relay', 4, 'hall', 'lights')

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("BB, GG")
