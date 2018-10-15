#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
from time import time
from .sql import saveLast

import logging

log = logging.getLogger(__name__)


class Device(object):
    """ Родительский класс устройств """
    def __init__(self):
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
        # Идентификатор устройтсва
        self.device_id = dvc_id
        # Имя группы
        self.group_name = group_name
        # Собственное имя
        self.name = name

        # Тип устройства
        self.type = 'Relay'
        # Инициализация родительского класса
        super(Relay, self).__init__()

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

    def form_cmd(self, data2parse):
        """ Метод формирования управляющей команды """
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
        # TODO: add command counter
        # Номер управляющей команды
        cmd[3] = 123

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
        if (inc_total == needed_states):
            # Если показания совпали
            log.info("OK")
            # Сохранить состояние реле в БД
            saveLast((inc_total, self.device_id))
            # Вернуть истину
            return True
        else:
            # Вернуть ложь
            return False
