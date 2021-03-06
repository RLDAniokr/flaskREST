#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import threading
from time import sleep, time

from .sencors import *
from .devices import *
from .firebase import fireBase
from . import sql
from .rfm69_lib.rfm69 import RFM69 as rfm69
from .rfm69_lib.configuration import RFM69Configuration as rfm_config
from .sencor_logging import Warden

import logging
log = logging.getLogger(__name__)


def singleton(class_):
    """ Декоратор для класса-одиночки """
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
    """ Класс-одиночка хаба Raspberry """
    def __init__(self):
        # Средства работы с Google Firebase
        self.firebase = fireBase()
        # Список групп устройств
        self.group_list = []
        # Список датчиков
        self.snc_list = []
        # Список устройств
        self.dvc_list = []
        self.cmd_queue = []
        # TODO: add get devices from db
        self.restore_settings_from_db()
        # rfm69hw module
        __config = rfm_config(chan_num=2)
        self.rfm = rfm69(dio0_pin=24,
                         reset_pin=22,
                         spi_channel=0,
                         config=__config)
        self.rfm.set_rssi_threshold(-114)
        # Инициализировать объект-логгер показаний датчиков
        self.warden = Warden(update_fb_fn=self.firebase.update_stats,
                             read_fb_fn=self.firebase.read_stats)
        # Инициализировать поток прослушки для статистики
        self.firebase.init_warden(handler=self.warden.stream_handler)
        # Инициализировать поток прослушки радиоканала
        self.init_read_sencors()

    # COMMON #

    def reset_fb_creds():
        """ Восстановление параметров входа для Firebase """
        # TODO: send password reset on email
        # TODO: save new email+pass in db
        # TODO: reauth with new email+pass
        pass

    def set_fb_creds(self, email, password):
        """ Установить параметры входа для Firebase """
        response = self.firebase.register_new_user(email, password)
        return response

    def restore_settings_from_db(self):
        """ Мтод восстановления устройств и групп из БД """
        # 1: Инициализировать группы
        __raw_groups = sql.getGroupNames()
        for raw_group in __raw_groups:
            self.add_group(raw_group[0])

        # 2: Инициализировать датчики
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

        # 3: Инициализировать управляемые устройства
        __raw_devices = sql.getDevicesSettings()
        log.info(__raw_devices)
        for raw_dvc in __raw_devices:
            self.add_dvc(
                dvc_id=raw_dvc[0],
                dvc_type=raw_dvc[1],
                dvc_group=raw_dvc[2],
                dvc_name=raw_dvc[3],
                ch0name=raw_dvc[4],
                ch1name=raw_dvc[5],
                last_val=raw_dvc[6],
                restore=True
            )

    def loop(self):
        """ Loop-worker для потока чтения/записи """
        try:
            while(True):
                # Проверить, жив ли основной поток
                assert(threading.main_thread().is_alive())
                # Проверить таймаут токена и обновить его при необходимости
                # TODO: set token-updater to diff thread with rLock
                self.firebase.upd_token(self.group_list, self.device_handler)
                # Если установлено событие отправки команд
                if self.rfm.wrt_event.is_set():
                    try:
                        # Отправка
                        self.write()
                    except Exception as e:
                        log.error("Error during command write")
                        log.error(e)
                else:
                    try:
                        # Чтение
                        self.read()
                    except Exception as e:
                        log.error("Error during snc/dvc read")
                        log.error(e)
                # Проверка датчиков на таймаут ответа и обновление их данных
                self.check_sencors_timeouts()
                self.firebase.update_time()
                log.info("===ITER===")
        except Exception as e:
            """Обработка непредвиденных исключений"""
            log.exception("message")
        finally:
            """ Убить потоки чтения устройств для чистого выхода """
            for group in self.group_list:
                try:
                    group.dvc_stream.close()
                except AttributeError:
                    # Обработка периодической ошибки аттрибута
                    # библиотечная ошибка, не влияющая ни на что
                    pass

    def read(self):
        """ Метод чтения радиоканала """
        # Переменная для хранения экземпляра датчика
        __sencor = None
        # Чтение пакета данных из радиоканала
        income = self.rfm.read_with_cb(30)
        # Если данные пришли, то тип income изменится на кортеж
        # Если не пришли income == None
        if type(income) == tuple:
            # Список с полезными данными
            __payload = income[0]
            # Проверка на целостность пакета
            if len(__payload) <= 1:
                log.error("Received damaged packet")
                return
            # Поиск экземпляра датчика
            __sencor = self.get_sencor_by_id(__payload[1])
            if __sencor is not None:
                # Сконвертировать принятые данные
                __sencor.convert_data(income[0])
                __sencor.convert_battery(income[0])
                # Вывести информацию в лог
                log.info(__sencor.name + ":" + __sencor.value)
                # Записать данные датчика в лог (если он нужного типа)
                self.warden.parse_n_write(snc_id=__sencor.sencor_id,
                                          snc_type=__sencor.type,
                                          snc_val=__sencor.value,
                                          snc_time=__sencor.last_response)
                # Обновить данные датчика в Firebase
                try:
                    self.firebase.update_sencor_value(__sencor)
                except Exception as e:
                    log.error("Error occured during sencor update")
                    log.error("Internet might be unavailable")
                    log.exception("message")
            else:
                # Поиск экземпляра устройства
                __device = self.get_device_by_id(__payload[1])
                # Если экземпляр найден
                if __device is not None:
                    # Обносить данные в памяти
                    __device.update_device(income[0])
                    # TODO: update data on FB
                    # TODO: try/exc to prevent failure

    def write(self):
        """ Метод отправки комманд из очереди в радиоканал """
        # Пока очередь команд не пуста
        while (len(self.cmd_queue) > 0):
            # "Выдернуть" команду из очереди
            __pack = self.cmd_queue.pop(0)
            # Сама команда
            __cmd = __pack[0]
            # Экземпляр устройства
            __dvc = __pack[1]
            # Статус отправки команды
            __status = False

            """ Отдельный набор операций для контроллера кондиционера """
            if (__dvc.type == "Conditioner"):
                # Время начала выполнения
                _start = time()
                # Если контроллеру еще не отправляли команды
                # (т.е. прием осуществляется сразу после маякового сообщения)
                if not __dvc.is_tamed:
                    while (time() - _start <= 40):
                        # Очистить событие записи
                        self.rfm.wrt_event.clear()
                        # Считать пакет из радиоканала
                        __rsp = self.rfm.read_with_cb(1)
                        # Если пришел пакет
                        if type(__rsp) == tuple:
                            # Если пришел маяк не от необходимого устройства
                            if __rsp[0][1] != __dvc.device_id:
                                # TODO: update incoming sencor
                                continue
                            # Ждать
                            sleep(0.05)
                            # Отправить команду
                            self.rfm.send_packet(__cmd)
                            # Обнулить событие записи
                            self.rfm.wrt_event.clear()
                            log.info("GOTCHA")
                            # Ждать ответа 1 сек
                            __rsp = self.rfm.read_with_cb(1)
                            # Если ответа не было
                            if type(__rsp) == tuple:
                                __status = __dvc.check_response(__cmd[4],
                                                                __rsp[0])
                            # Если пришел ответ, проверить его
                            if (__status):
                                # Если совпадают номер отпрвленной команды и
                                # id устройства в ответе, то считаем контроллер
                                # "укрощенным"
                                __dvc.is_tamed = True
                                # Вывод в лог сообщение об успехе
                                log.info("CONDER %s: SENT AND TAMED")
                                # Выход из цикла while
                                break
                    if not __status:
                        __dvc.rollback()
                        self.firebase.update_device_value(__dvc)

                # Если контроллер уже был в управлении
                else:
                    # Промежуточное хранение последнего ответа
                    _lr = __dvc.last_response
                    # Цикл по времени (попытки отправки в течение 26 сек)
                    while(time() - _start < 26):
                        # Для временного окна после маяка установить
                        # дополнительную задержку
                        if (round((time() - _lr) % 10) == 0):
                            __add_gap = 0.05
                        else:
                            __add_gap = 0
                        # Вычисление временного окна для отправки команды
                        # Каждые 5 сек
                        __t_diff = (time() - _lr) % 5
                        # Условие вхождения во временное окно (20 мс)
                        _time_to_send = (__t_diff <= 0.02) and (__t_diff >= 0)
                        if (_time_to_send):
                            sleep(__add_gap)
                            # Отправить пакет
                            self.rfm.send_packet(__cmd)
                            # Очистить событие отправки
                            self.rfm.wrt_event.clear()

                            # Подождать ответ
                            __rsp = self.rfm.read_with_cb(1)
                            # Если ответ пришел
                            if type(__rsp) == tuple:
                                # Ппроверить статус ответа
                                __status = __dvc.check_response(__cmd[3],
                                                                __rsp[0])
                                # При правильном ответе лог и выход из цикла
                                if __status:
                                    log.info("Conditioner command sent")
                                    break
                # Если за 26 сек команда не была отправлена
                if not __status:
                    # Лог ошибки
                    __dvc.rollback()
                    self.firebase.update_device_value(__dvc)
                    log.info("Conditioner command sending failed")

                # Возврат к изъятию команды из очереди
                continue

            # 5 попыток отправки
            for i in range(0, 5):
                # Установка события отправки
                self.rfm.wrt_event.set()
                # Отправка команды
                self.rfm.send_packet(__cmd)
                # Очистка события отправки
                self.rfm.wrt_event.clear()

                # Ожидпние ответа
                __response = self.rfm.read_with_cb(1)

                # Если пришел ответ
                if type(__response) == tuple:
                    # Проверка статуса ответа
                    __status = __dvc.check_response(__cmd[4], __response[0])
                    # Если статус отвтеа положительный
                    if (__status):
                        # Лог и выход из for(0, 5)
                        log.info("Command sent successfully")
                        break
            # Если статус не был получен
            if not __status:
                # Лог ошибки
                log.info("Command sending failed")
                __dvc.rollback()
                self.firebase.update_device_value(__dvc)
        # Очистка события отправки
        self.rfm.wrt_event.clear()

    def device_handler(self, message):
        """ Метод-обработчик сообщений от облачной базы Firebase """
        # Имя группы
        __from = message["stream_id"]
        # Имя устройства
        __inc_device_name = (message["path"].split("/"))[1]
        # Полезные данные
        __data = message["data"]
        # Переменная для экземпляра устройства
        __dvc2wrt = None

        # Поиск экземпляра устройства
        for dvc in self.dvc_list:
            if dvc.name == __inc_device_name:
                __dvc2wrt = dvc
                break

        # Если устройство найдено
        if __dvc2wrt is not None:
            # Сформировать команду для отправки
            cmd = __dvc2wrt.form_cmd(__data)
            # Добавить пару [команда, экземпляр] в очередь
            self.cmd_queue.append([cmd, __dvc2wrt])
            # Установить событие отправки команд
            self.rfm.wrt_event.set()

    def init_read_sencors(self):
        # Инициализировать тред
        self.read_thread = threading.Thread(name='rw', target=self.loop)
        # Установить тред как демон
        self.read_thread.daemon = True
        # Запустить тред
        self.read_thread.start()

    def check_sencors_timeouts(self):
        for sencor in self.snc_list:
            if sencor.check_timeout():
                log.error("TIMEOUT detected: %s" % sencor.name)
                log.error("Time: %s sec" % (time() - sencor.last_response))
                self.firebase.update_sencor_value(sencor)

    # GROUPS #

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

    def get_groups(self):
        """ Метод получения списка имен групп """
        __groups = {}
        for group in self.group_list:
            __groups[group.name] = self.get_group_info(group.name)
        return __groups

    def get_group_info(self, group_name):
        """
            Метод получения словаря с датчиками и устройствами,
            привязанными к группе
            Если группы с данным именем не существует, вернет FAIL (str)
        """
        __group = self.get_group_by_name(group_name)
        if __group is None:
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

    def add_group(self, group_name):
        """
            Добавить новую группу.
            Если группа с таким именем уже существует, возвращает FAIL (str)
        """
        if self.get_group_by_name(group_name) is not None:
            return "FAIL"

        _new_grp = Group(group_name)
        self.group_list.append(_new_grp)
        try:
            _new_grp.dvc_stream = self.firebase.set_strm(self.device_handler,
                                                         _new_grp.name)
        except Exception as e:
            log.error("Error in group appending")
            log.error("Internet might be unavailable")
            log.exception("message")
            return("FAIL")

        return("OK")

    def remove_group(self, group_name):
        """
            Удалить существующую группу.
            Если группы с таким именем не существует, возвращает FAIL (str)
            Если группа не пуста, возвращает FAIL
        """
        __group = self.get_group_by_name(group_name)
        if __group is None:
            return "FAIL"
        else:
            if len(__group.sencors) > 0:
                return "FAIL"
            if len(__group.devices) > 0:
                return "FAIL"
            try:
                __group.dvc_stream.close()
            except AttributeError:
                pass
            self.firebase.delete_group(__group.name)
            self.group_list.remove(__group)
            return "OK"

    # SENCORS #

    def get_sencor_by_id(self, s_id):
        """
            Вспомогательный метод поиска датчика в списке по типу и id.
            При успешном нахождении возвращает экземпляр датчика
            При безуспешном поиске возвращает None
        """
        __snc = None
        for s in self.snc_list:
            if s.sencor_id == s_id:
                __snc = s
                break
        return __snc

    def add_snc(self, snc_type, snc_id, snc_group, snc_name, restore=False):
        """ Добавить датчик """
        # Проверить, существует ли уже такой датчик
        if self.get_sencor_by_id(snc_id) is not None:
            log.error("Sencor with this type/id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(snc_group)
        if __group is None:
            log.error("Group %s not find" % snc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if snc_type == "Temperature":
            new_sencor = TemperatureSencor(snc_id=snc_id,
                                           group_name=snc_group,
                                           name=snc_name)
        elif snc_type == "Humidity":
            new_sencor = HumiditySencor(snc_id=snc_id,
                                        group_name=snc_group,
                                        name=snc_name)
        elif snc_type == "Luminosity":
            new_sencor = LuminositySencor(snc_id=snc_id,
                                          group_name=snc_group,
                                          name=snc_name)
        elif snc_type == "Door":
            new_sencor = DoorSencor(snc_id=snc_id,
                                    group_name=snc_group,
                                    name=snc_name)
        elif snc_type == "Pulse":
            new_sencor = PulseSencor(snc_id=snc_id,
                                     group_name=snc_group,
                                     name=snc_name)
        elif snc_type == "Water":
            new_sencor = WaterCounter(snc_id=snc_id,
                                      group_name=snc_group,
                                      name=snc_name)
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

    def edit_snc(self, snc_type, snc_id, new_snc_group, new_snc_name):
        """ Редактировать настройки датчика """
        __sencor_for_edit = self.get_sencor_by_id(snc_id)

        __new_group = self.get_group_by_name(new_snc_group)
        if __new_group is None:
            log.error("New group does not exists")
            return "FAIL"

        if __sencor_for_edit is not None:
            __old_group = self.get_group_by_name(__sencor_for_edit.group_name)
            __old_group.sencors.remove(__sencor_for_edit)
            self.firebase.delete_sencor(__sencor_for_edit)

            __sencor_for_edit.group_name = new_snc_group
            __sencor_for_edit.name = new_snc_name
            __new_group.sencors.append(__sencor_for_edit)
            self.firebase.update_sencor_value(__sencor_for_edit)
            sql.editSencor((new_snc_group, new_snc_name, snc_id))
            return "OK"
        else:
            log.error("Sencor for edit not found in list")
            return "FAIL"

    def remove_snc(self, snc_type, snc_id):
        """ Удалить датчик """
        __sencor_for_delete = self.get_sencor_by_id(snc_id)

        if __sencor_for_delete is not None:
            self.snc_list.remove(__sencor_for_delete)
            __group = self.get_group_by_name(__sencor_for_delete.group_name)
            __group.sencors.remove(__sencor_for_delete)
            sql.deleteSencor(snc_id)
            self.firebase.delete_sencor(__sencor_for_delete)
            return "OK"
        else:
            log.error("Sencor for delete not found in list")
            return "FAIL"

    # DEVICES #

    def get_device_by_id(self, d_id):
        """
            Вспомогательный метод поиска устройства в списке по типу и id.
            При успешном нахождении возвращает экземпляр устройства
            При безуспешном поиске возвращает None
        """
        __dvc = None
        for d in self.dvc_list:
            if d.device_id == d_id:
                __dvc = d
                break
        return __dvc

    def add_dvc(self, dvc_type, dvc_id, dvc_group, dvc_name, ch0name=None,
                ch1name=None, last_val=None, restore=False):
        """ Добавить устройство """
        # Проверить, существует ли уже такое устройство
        if self.get_device_by_id(dvc_id) is not None:
            log.error("Device with this id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(dvc_group)
        if __group is None:
            log.error("Group %s not find" % dvc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if dvc_type == "Relay":
            new_device = Relay(dvc_id=dvc_id,
                               group_name=dvc_group,
                               name=dvc_name,
                               ch0name=ch0name,
                               ch1name=ch1name,
                               last_val=last_val)
        elif dvc_type == "Conditioner":
            new_device = Conditioner(dvc_id=dvc_id,
                                     group_name=dvc_group,
                                     name=dvc_name,
                                     last_val=last_val)
        else:
            log.error("Unknown device type")
            return "FAIL"

        # Если создается новое устройство (не восстанавливается из БД)
        if not restore:
            # Добавить новую запись в БД
            __dvc_settings = (dvc_id,
                              dvc_type,
                              dvc_group,
                              dvc_name,
                              ch0name,
                              ch1name,
                              0)
            sql.newDeviceSettings(__dvc_settings)
        # Добавить новое устройство в список устройств хаба и группы
        self.dvc_list.append(new_device)
        __group.devices.append(new_device)
        # TODO: init stuff in first/recover send
        self.firebase.update_device_value(new_device)
        return "OK"

    def edit_dvc(self, dvc_type, dvc_id, new_dvc_group, new_dvc_name,
                 new_ch0name=None, new_ch1name=None):
        """ Редактировать настройки устройства """
        __device_for_edit = self.get_device_by_id(dvc_id)

        __new_group = self.get_group_by_name(new_dvc_group)
        if __new_group is None:
            log.error("New group does not exists")
            return "FAIL"

        if __device_for_edit is not None:
            __old_group = self.get_group_by_name(__device_for_edit.group_name)
            __old_group.devices.remove(__device_for_edit)
            self.firebase.delete_device(__device_for_edit)

            __device_for_edit.group_name = new_dvc_group
            __device_for_edit.name = new_dvc_name
            if __device_for_edit.type == 'Relay':
                __device_for_edit.ch0name = new_ch0name
                __device_for_edit.ch1name = new_ch1name
            __new_group.devices.append(__device_for_edit)
            self.firebase.update_device_value(__device_for_edit)
            __dvc_settings = (new_dvc_group,
                              new_dvc_name,
                              new_ch0name,
                              new_ch1name,
                              dvc_id)
            sql.editDevice(__dvc_settings)
            return "OK"
        else:
            log.error("Device for edit not found in list")
            return "FAIL"

    def remove_dvc(self, dvc_type, dvc_id):
        """ Удалить устройство """
        __device_for_delete = self.get_device_by_id(dvc_id)

        if __device_for_delete is not None:
            self.dvc_list.remove(__device_for_delete)
            __group = self.get_group_by_name(__device_for_delete.group_name)
            __group.devices.remove(__device_for_delete)
            sql.deleteDevice(dvc_id)
            self.firebase.delete_device(__device_for_delete)
            return "OK"
        else:
            log.error("Device for delete not found in list")
            return "FAIL"
