#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

# TODO: import stuff
import threading
from time import sleep, time

from .sencors import *
from .devices import *
from .firebase import fireBase
from . import sql

import logging
log = logging.getLogger(__name__)

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


class Group(object):
    """ Класс группы устройств (кухня/улица и т.п.) """
    def __init__(self, name):
        self.name = name
        self.sencors = []
        self.devices = []

@singleton
class rpiHub(object):
    """ Класса хаба Raspberry """
    def __init__(self):
        # Средства работы с Google Firebase
        self.firebase = fireBase()
        # Список групп устройств
        self.group_list = []
        # Список датчиков
        self.snc_list = []
        # TODO: add get sencors from db
        # Список устройств
        self.dvc_list = []
        # TODO: add get devices from db
        self.restore_settings_from_db()
        # Инициализировать поток прослушки радиоканала
        self.init_read_sencors()

    def restore_settings_from_db(self):
        # 1: Get and initiate groups
        __raw_groups = sql.getGroupNames()
        for raw_group in __raw_groups:
            self.add_group(raw_group[0])

        log.info("GET GROUPS: %s" % self.get_groups())

        # 2: Get and initiate sencors
        __raw_sencors = sql.getSencorsSettings()
        log.info(__raw_sencors)
        for raw_snc in __raw_sencors:
            self.add_snc(
                snc_id=raw_snc[0],
                snc_type=raw_snc[1],
                snc_group=raw_snc[2],
                snc_name=raw_snc[3],
                restore=True
            )

        # 3: Get and initiate devices
        __raw_devices = sql.getDevicesSettings()
        log.info(__raw_devices)
        for raw_dvc in __raw_devices:
            self.add_dvc(
                dvc_id=raw_dvc[0],
                dvc_type=raw_dvc[1],
                dvc_group=raw_dvc[2],
                dvc_name=raw_dvc[3],
                restore=True
            )

        for gr in self.group_list:
            log.critical(gr.name)

    def read(self):
        # TEMP
        log.info("Read thread initialized")
        try:
            while(True):
                pass
                #__start = time()
                __idx = randint(0, len(self.snc_list)-1)
                snc = self.snc_list[__idx]
                snc.get_random_state()
                log.info("Sencor %s:%s" % (snc.name, snc.value))
                self.firebase.upd_token(self.group_list, self.device_handler)
                self.firebase.update_sencor_value(snc)
                # # TODO: send value to firebase
                log.critical("===ITER===")
                #log.critical("TIEM: %s" %(time()-__start))
                sleep(5)
        except KeyboardInterrupt:
            "Got exception kbu"
            for g in self.group_list:
                g.dvc_stream.close()

    def init_read_sencors(self):
        # Инициализировать тред
        self.read_thread = threading.Thread(target=self.read)
        # Установить тред как демон
        self.read_thread.daemon = True
        # Запустить тред
        self.read_thread.start()

    def get_group_by_name(self, name):
        """
            Вспомогательный метод поиска группы в списке по имени.
            При успешном нахождении возвращает экземпляр группы
            При безуспешном поиске возвращает None
        """
        __group = None
        for g in self.group_list:
            if g.name == name:
                __group = g
                break
        return __group

    def get_sencor_by_typid(self, type, s_id):
        """
            Вспомогательный метод поиска датчика в списке по типу и id.
            При успешном нахождении возвращает экземпляр датчика
            При безуспешном поиске возвращает None
        """
        __snc = None
        for s in self.snc_list:
            if s.type == type:
                if s.sencor_id == s_id:
                    __snc = s
                    break
        return __snc

    def get_device_by_typid(self, type, d_id):
        """
            Вспомогательный метод поиска устройства в списке по типу и id.
            При успешном нахождении возвращает экземпляр устройства
            При безуспешном поиске возвращает None
        """
        __dvc = None
        for d in self.dvc_list:
            if d.type == type:
                if d.device_id == d_id:
                    __dvc = d
                    break
        return __dvc

    def get_groups(self):
        """ Метод получения списка имен групп """
        __group_names = []
        for group in self.group_list:
            __group_names.append(group.name)
        return __group_names

    def get_group_info(self, group_name):
        """
            Метод получения словаря с датчиками и устройствами,
            привязанными к группе
            Если группы с данным именем не существует, вернет FAIL (str)
        """
        __group = self.get_group_by_name(group_name)
        if __group == None:
            return "FAIL"
        __snc_output = []
        for sencor in __group.sencors:
            __snc_output.append(sencor.get_info())
        __dvc_output = []
        for device in __group.devices:
            __dvc_output.append(device.get_info())
        response = {
            'sencors': __snc_output,
            'devices': __dvc_output
        }
        return response

    def device_handler(self, message):
        """ Метод-обработчик сообщений от облачной базы Firebase """
        __from = message["stream_id"]
        #__group = self.get_group_by_name(__from)
#        if __group == None:
#            log.error("Incoming message from non-existing group")
#            return
        __inc_device_name = (message["path"].split("/"))[1]
        __data = message["data"]
        log.info("GROUP: %s, DEVICE: %s, DATA: %s" % (__from, __inc_device_name, __data))
        #__device = None

    def add_group(self, group_name):
        """
            Добавить новую группу.
            Если группа с таким именем уже существует, возвращает FAIL (str)
        """
        if self.get_group_by_name(group_name) != None:
            return "FAIL"

        __new_group = Group(group_name)
        self.group_list.append(__new_group)
        # TODO: subscribe devices
        log.info("Type in set: %s" % type(group_name))
        __new_group.dvc_stream = self.firebase.root(group_name).child('devices').stream(self.device_handler, stream_id=__new_group.name, token=self.firebase.token)
        log.info("Type stream in make: %s" %__new_group.dvc_stream)
        return("OK")

    def remove_group(self, group_name):
        """
            Удалить существующую группу.
            Если группы с таким именем не существует, возвращает FAIL (str)
            Если группа не пуста, возвращает FAIL
        """
        __group = self.get_group_by_name(group_name)
        if __group == None:
            return "FAIL"
        else:
            if len(__group.sencors) > 0:
                return "FAIL"
            if len(__group.devices) > 0:
                return "FAIL"
            # TODO: Kill listen stream
            # TODO: kill firebase reference in sencors/devices
            self.group_list.remove(__group)
            return "OK"

    def add_snc(self, snc_type, snc_id, snc_group, snc_name, restore=False):
        """ Добавить датчик """
        # Проверить, существует ли уже такой датчик
        if self.get_sencor_by_typid(snc_type, snc_id) != None:
            log.error("Sencor with this type/id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(snc_group)
        if __group == None:
            log.error("Group %s not find" % snc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if snc_type == "Temperature":
            new_sencor = TemperatureSencor(snc_id=snc_id, group_name=snc_group, name=snc_name)
        elif snc_type == "Humidity":
            new_sencor = HumiditySencor(snc_id=snc_id, group_name=snc_group, name=snc_name)
        elif snc_type == "Luminosity":
            new_sencor = LuminositySencor(snc_id=snc_id, group_name=snc_group, name=snc_name)
        else:
            log.error("Unknown sencor type")
            return "FAIL"

        # Если создается новое устройство (не восстанавливается из БД)
        if not restore:
            # Добавить новую запись в БД
            sql.newSencorSettings((snc_id, snc_type, snc_group, snc_name))
        # Добавить новый датчик в список датчиков хаба и группы
        self.snc_list.append(new_sencor)
        __group.sencors.append(new_sencor)
        self.firebase.update_sencor_value(new_sencor)
        return "OK"

    def add_dvc(self, dvc_type, dvc_id, dvc_group, dvc_name, restore=False):
        """ Добавить устройство """
        # Проверить, существует ли уже такое устройство
        if self.get_device_by_typid(dvc_type, dvc_id) != None:
            log.error("Device with this type/id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(dvc_group)
        if __group == None:
            log.error("Group %s not find" % dvc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if dvc_type == "Relay":
            new_device = Relay(dvc_id=dvc_id, group_name=dvc_group, name=dvc_name)
        else:
            log.error("Unknown device type")
            return "FAIL"

        # Если создается новое устройство (не восстанавливается из БД)
        if not restore:
            # Добавить новую запись в БД
            sql.newDeviceSettings((dvc_id, dvc_type, dvc_group, dvc_name))
        # Добавить новое устройство в список устройств хаба и группы
        self.dvc_list.append(new_device)
        __group.devices.append(new_device)
        # TODO: init stuff in first/recover send
        self.firebase.update_device_value(new_device)
        return "OK"


    def edit_snc(self, snc_type, snc_id, new_snc_group, new_snc_name):
        """ Редактировать настройки датчика """
        __sencor_for_edit = self.get_sencor_by_typid(snc_type, snc_id)

        __new_group = self.get_group_by_name(new_snc_group)
        if __new_group == None:
            log.error("New group does not exists")
            return "FAIL"

        if __sencor_for_edit != None:
            __old_group = self.get_group_by_name(__sencor_for_edit.group_name)
            __old_group.sencors.remove(__sencor_for_edit)
            self.firebase.delete_sencor(__sencor_for_edit)

            __sencor_for_edit.group_name = new_snc_group
            __sencor_for_edit.name = new_snc_name
            __new_group.sencors.append(__sencor_for_edit)
            self.firebase.update_sencor_value(__sencor_for_edit)
            sql.editSencor((new_snc_group, new_snc_name, snc_id, snc_type))
            return "OK"
        else:
            log.error("Sencor for edit not found in list")
            return "FAIL"


    def edit_dvc(self, dvc_type, dvc_id, new_dvc_group, new_dvc_name):
        """ Редактировать настройки устройства """
        __device_for_edit = self.get_device_by_typid(dvc_type, dvc_id)

        __new_group = self.get_group_by_name(new_dvc_group)
        if __new_group == None:
            log.error("New group does not exists")
            return "FAIL"

        if __device_for_edit != None:
            __old_group = self.get_group_by_name(__device_for_edit.group_name)
            __old_group.devices.remove(__device_for_edit)
            self.firebase.delete_device(__device_for_edit)

            __device_for_edit.group_name = new_dvc_group
            __device_for_edit.name = new_dvc_name
            __new_group.devices.append(__device_for_edit)
            self.firebase.update_device_value(__device_for_edit)
            sql.editDevice((new_dvc_group, new_dvc_name, dvc_id, dvc_type))
            return "OK"
        else:
            log.error("Device for edit not found in list")
            return "FAIL"

    def remove_snc(self, snc_type, snc_id):
        """ Удалить датчик """
        __sencor_for_delete = self.get_sencor_by_typid(snc_type, snc_id)

        if __sencor_for_delete != None:
            self.snc_list.remove(__sencor_for_delete)
            __group = self.get_group_by_name(__sencor_for_delete.group_name)
            __group.sencors.remove(__sencor_for_delete)
            sql.deleteSencor((snc_id, snc_type))
            self.firebase.delete_sencor(__sencor_for_delete)
            return "OK"
        else:
            log.error("Sencor for delete not found in list")
            return "FAIL"

    def remove_dvc(self, dvc_type, dvc_id):
        """ Удалить устройство """
        __device_for_delete = self.get_device_by_typid(dvc_type, dvc_id)

        if __device_for_delete != None:
            self.dvc_list.remove(__device_for_delete)
            __group = self.get_group_by_name(__device_for_delete.group_name)
            __group.devices.remove(__device_for_delete)
            sql.deleteDevice((dvc_id, dvc_type))
            self.firebase.delete_device(__device_for_delete)
            return "OK"
        else:
            log.error("Device for delete not found in list")
            return "FAIL"

if __name__ == '__main__':
    hub = rpiHub()
