#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
from time import time
from .sql import saveLast

import logging

log = logging.getLogger(__name__)


class Device(object):
    """ Родительский класс устройств """
    def __init__(self, dvc_id, group_name, name):
        # Идентификатор устройтсва
        self.device_id = dvc_id
        # Имя группы
        self.group_name = group_name
        # Собственное имя
        self.name = name

        # Порядковый номер управляющей команды
        self.cmd_num = 0

        # Время последнего ответа
        self.last_response = time()

    def get_info(self):
        """ Метод получения информации об устройстве """
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
        # Инициализация родительского класса
        super(Relay, self).__init__(dvc_id, group_name, name)
        # Тип устройства
        self.type = 'Relay'

        # Имя нулевого канала
        self.ch0name = ch0name
        # Имя первого канала
        self.ch1name = ch1name

        # Если нет информации о последнем состоянии реле
        if last_val is None:
            # Установить оба канала в False
            self.ch0val = False
            self.ch1val = False
        else:
            # Если имеютя данные о последнем состоянии реле
            # Разбиение битов и приведение к типу bool
            self.ch0val = (last_val & 1) == 1
            self.ch1val = ((last_val >> 1) & 1) == 1

        self.ch0old = self.ch0val
        self.ch1old = self.ch0val

    def get_info(self):
        """ Переопределение мметода получения информации об устройстве """
        response = {
            'dvc_id': self.device_id,
            'dvc_type': self.type,
            'group_name': self.group_name,
            'name': self.name,
            'ch0name': self.ch0name,
            'ch1name': self.ch1name
        }
        return response

    def form_data(self):
        data = {
            self.name + '/type': self.type,
            self.name + '/id': self.sencor_id,
            self.name + '/' + self.ch0name: self.ch0val,
            self.name + '/' + self.ch1name: self.ch1val,
        }
        return data

    def update_device(self, income):
        self.last_response = time()
        # TODO: update device values on ram & FB

    def form_cmd(self, data2parse):
        """ Метод формирования управляющей команды """
        self.ch0old = self.ch0val
        self.ch1old = self.ch1val
        if self.ch0name in data2parse:
            # Если пришла команда управления нулевым каналом
            self.ch0val = data2parse[self.ch0name]
        elif self.ch1name in data2parse:
            # Если пришла команда управления первым каналом
            self.ch1val = data2parse[self.ch1name]

        # Скелет пакета для отправки
        cmd = [0, 0, 0, 0, 0]
        # Идентификатор адресата
        cmd[0] = self.device_id
        # Идентификатор Raspberry
        cmd[1] = 0
        # Идентификатор типа устройств "Реле"
        cmd[2] = 14
        # Номер управляющей команды
        if self.cmd_num < 255:
            self.cmd_num += 1
        else:
            self.cmd_num = 0

        cmd[3] = self.cmd_num

        # Старший бит
        __sb = 0b10 if self.ch1val else 0b00
        #  Младший бит
        __lb = 0b01 if self.ch0val else 0b00
        # Побитовое сложение
        cmd[4] = __sb + __lb

        return cmd

    def check_response(self, needed_states, income):
        """ Метод проверки ответа на управляющую команду """
        if income[1] != self.device_id:
            # Если ответ не от реле
            return False
        if ((income[5] & 0b1000)+(income[5] & 0b0010)) != 0:
            # Если установлены биты повреждения каналов
            return False
        # Побитовое сложения битов состояния каналов
        inc_total = ((income[5] & 0b0100) >> 1) + (income[5] & 0b0001)
        # Если показания совпали
        if (inc_total == needed_states):
            # Сохранить состояние реле в БД
            saveLast((inc_total, self.device_id))
            self.ch1old = (needed_states >> 1 == 1)
            self.ch0old = (needed_states & 0b1 == 1)
            # Вернуть истину
            return True
        else:
            # Вернуть ложь
            return False

    def rollback(self):
        self.ch0val = self.ch0old
        self.ch1val = self.ch1old


class Conditioner(Device):
    """ Класс контроллера кондиционера"""
    def __init__(self, dvc_id, group_name, name, last_val):
        # Инициализация родительского класса
        super(Conditioner, self).__init__(dvc_id, group_name, name)
        # Тип устройства
        self.type = "Conditioner"
        # Флаг факта управления
        self.is_tamed = False

        # Последнее успешное значение управления
        self.value = last_val or 0
        # Бэкап последнего успешного знчения управления
        self.old_value = self.value

        # Кодовые обозначения режимов работы
        self.mode_codes = ("AUTO", "COOL", "DRY", "VENT", "HEAT")
        # Кодовые обозначения углов диффузора
        self.angle_codes = ("AUTO", "TOP", "HTOP", "HBOT", "BOT")

        # Откат занчений параметров управления
        self.rollback()

    def form_data(self):
        data = {
            self.name + "/power": self.power,
            self.name + "/mode": self.mode,
            self.name + "/temp": self.temp,
            self.name + "/speed": self.speed,
            self.name + "/angle": str(self.angle),
        }
        return data


    def update_device(self, income):
        """ Обновление данных """
        # Обновление времени последнего ответа
        self.last_response = time()
        # Флаг факта управления
        self.is_tamed = True if (income[7] != 0) else False
        # Обновление показаний
        self.value = ((income[5] & 0b1) == 1)
        self.rollback()

    def form_cmd(self, data2parse):
        """ Метод формирования управляющей команды
            @param: data2parse - словарь/json с параметрами управления
            @return: list - список со сформированной командой
        """
        # Скелет пакета для отправки
        cmd = [0, 0, 0, 0, 0, 0]
        # Идентификатор адресата
        cmd[0] = self.device_id
        # Идентификатор Raspberry
        cmd[1] = 0
        # Идентификатор типа устройств "Контроллер кондиционера"
        cmd[2] = 17
        # Номер управляющей команды (инкремент + присвоение)
        if self.cmd_num < 255:
            self.cmd_num += 1
        else:
            self.cmd_num = 0

        cmd[3] = self.cmd_num

        self.old_value = self.value
        # Парсинг пришедшего сообщения по ключам
        if 'power' in data2parse:
            self.power = data2parse['power']
        if 'mode' in data2parse:
            self.mode = data2parse['mode']
        if 'temp' in data2parse:
            self.temp = data2parse['temp']
        if 'speed' in data2parse:
            self.speed = int(data2parse['speed'])
        if 'angle' in data2parse:
            self.angle = data2parse['angle']

        # Конкатенация настроек
        self.value = (1 if self.power else 0) | \
                     (self.mode_codes.index(self.mode) << 1) | \
                     ((self.temp - 16) << 4) | \
                     (self.speed << 8) | \
                     (self.angle_codes.index(self.angle) << 11)

        # Разбиение по байтам
        cmd[4] = self.value & 0xFF
        cmd[5] = (self.value >> 8) & 0xFF

        log.warning("POW: %s" % (cmd[4] & 1))
        log.warning("MOD: %s" % (cmd[4] >> 1 & 7))
        log.warning("TEMP: %s" % (cmd[4] >> 4 & 7))
        log.warning("SPEED: %s" % (cmd[5] & 0x7))
        log.warning("DIFF: %s" % (cmd[5] >> 3))
        return cmd

    def check_response(self, cmd_n, income):
        """ Метод проверки ответа от устройства
            @param: cmd_n - номер управл. команды из отправленного пакета
            @param: income - список с ответтом от устройства
            @return: status - правильность отклика (True/False)
        """
        if income[1] == self.device_id:
            if income[7] == cmd_n:
                # Если идентификатор и номер команды совпали
                # Сохранить значение в базе
                saveLast((self.value, self.device_id))
                # Вернуть True
                return True
            else:
                self.update_device(income)
        else:
            return False

    def rollback(self):
        """ Метод отката изменений при ошибке/восстановлении """
        self.value = self.old_value
        self.power = (self.value & 0x1) == 1
        self.mode = self.mode_codes[((self.value >> 1) & 0x7)]
        self.temp = ((self.value >> 4) & 0xF) + 16
        self.speed = ((self.value >> 8) & 0x7)
        self.angle = self.angle_codes[((self.value >> 11) & 0x7)]
