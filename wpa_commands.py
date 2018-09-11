#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
"""
    Модуль работы с wpa_cli через интерфейс командной строки (subprocess)
"""

# Подключение логгера
import logging
# Подключение модуля работы с подпроцессами
import subprocess as sbp
# Подключение модуля работы с регулярными выражениями
import re
# Модуль для временной задержки
from time import sleep

# Логгер
LOG = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Исключение при обработке подключении сети"""
    def __init__(self):
        super(ConnectionError, self).__init__()
        self.msg = "Error during establishing connection"

    def __str__(self):
        return self.msg


class DisconnectionError(Exception):
    """Исключение при обработке отключении сети"""
    def __init__(self):
        super(DisconnectionError, self).__init__()
        self.msg = "Error during disconnect"

    def __str__(self):
        return self.msg


# in: void
# out: dict/json
def wpa_status():
    """ Функция запроса текущего статуса интерфейса wlan0 """
    # Вывод (dict/json)
    output = {}
    # Аргументы для shell
    args = ['wpa_cli', '-i', 'wlan0', 'status']
    try:
        # Раздзеление вывода по символу новой строки в список
        statusOutput = sbp.check_output(args).decode('utf-8').split("\n")  # (list)
        status = {}  # dict
        # Разбить каждую из строк на пары "ключ":"занчение"
        for line in statusOutput[:len(statusOutput)-1]:
            # Разбить строку по разделителю "="
            prop, val = line.split("=")
            status[prop] = val
        # Вывод
        output = {
            "status": "OK",
            "message": "Status service.",
            "payload": status
        }
    # Поймать и внести в лог исключение
    except Exception as e:
        LOG.error("Error occured during status check")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Status service.",
            "payload": None
        }
    return output


# in: void
# out: dict/json
def wpa_scan():
    """ Функция для проведения сканирования и возврата списка сетей """
    # Вывод dict/json
    output = {}
    try:
        # Аргументы для выполнения сканирования (shell)
        scanCommandArgs = ['wpa_cli', '-i', 'wlan0', "scan"]
        # Аргументы для вывода списка просканированных сетей
        scanListArgs = ['wpa_cli', '-i', 'wlan0', "scan_results"]
        # Если команда на старт сканирования выполнена успешно
        if (sbp.call(scanCommandArgs) == 0):
            # Подождать 1 сек
            sleep(1)
            # Забрать список сетей и разделить его в список
            tmp = sbp.check_output(scanListArgs).decode('utf-8').split("\n")  # list

            listNetworks = {}  # dict/json
            # Для каждого из элементов списка
            for line in tmp[1:len(tmp)-1]:
                # Рзаделить строку по символу табуляции
                div_line = line.split("\t")
                # Разделение свойств в словарь ("ключ":"значение")
                props = {
                    "bssid": div_line[0],
                    "frequency": div_line[1],
                    "SignalLevel": div_line[2],
                    "flags": div_line[3],
                    "ssid": div_line[4],
                }
                # Добавление сети в общий вывод "Имя_сети":{свойства_сети}
                listNetworks[div_line[4]] = props
            # Вывод (dict/json)
            output = {
                "status": "OK",
                "message": "Status service.",
                "payload": listNetworks
            }
    # Обработка исключения
    except Exception as e:
        LOG.error("Error occured during scan")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Networks",
            "payload": None
        }
    return output


# in: void
# out: dict/json
def wpa_disconnect():
    """ Функция для отключения от сетей """
    # Вывод dict/json
    output = {}
    try:
        # Аргументы shell для переведения интерфейса в статус "DISCONNECTED"
        dcArgs = ['wpa_cli', '-i', 'wlan0', 'disconnect']
        # Выполенение shell команды на отключение
        dcStatus = sbp.check_output(dcArgs).decode('utf-8')
        # Если команда не прошла
        if dcStatus != "OK\n":
            LOG.error("Error during disconnect")
            raise DisconnectionError

        # Аргументы shell команды на вывод списка сохраненных сетей
        listArgs = ['wpa_cli', '-i', 'wlan0', 'list_networks']
        # Выполнение shell команды на вывод списка сохраненных сетей
        listNetworks = sbp.check_output(listArgs).decode('utf-8').split("\n")  # list

        # Для каждого из элементов списка
        # NOTE: первая строка - наименования свойств сетей, а последняя-пустая
        for network in listNetworks[1:len(listNetworks)-1]:
            # Разделить по табуляции и забрать идентификатор сети (str)
            networkId, _ = network.split("\t", 1)
            # Выполнить удаление сети из списка сохраненных
            rmNetArgs = ['wpa_cli', '-i', 'wlan0', 'remove_network', networkId]
            rmNetOut = sbp.check_output(rmNetArgs).decode('utf-8')
            # Если удаление прошло с ошибкой
            if rmNetOut != "OK\n":
                LOG.error("Error occured during network removal")
                LOG.error("Network id: %s" % networkId)
                raise DisconnectionError

        # Перевести интерфейс в статус "INACTIVE"
        reasArgs = ['wpa_cli', '-i', 'wlan0', 'reassociate']
        reasStatus = sbp.check_output(reasArgs).decode('utf-8')
        if reasStatus != "OK\n":
            LOG.error("Error occured during network reassociate")
            raise DisconnectionError

        # Сохранить конфигурацию wpa_supplicant
        saveArgs = ['wpa_cli', '-i', 'wlan0', 'save_config']
        saveOut = sbp.check_output(saveArgs)

        # Вывод dict/json
        output = {
            "status": "OK",
            "message": "Disconnect service.",
            "payload": ""
        }

    # Обработка исключений
    except Exception as e:
        LOG.error("Error occured while disconnect")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Disconnect service.",
            "payload": ""
        }
    return output


# in: str, str
# out: dict/json
def wpa_connect(ssid, psk):
    """ Функция для подключения к сети """
    # Вывод dict/json
    output = {}
    # Статус
    state = ""
    # Ip в подключенной сети
    ip = ""
    # Отключиться перед новым соединением
    wpa_disconnect()

    try:
        # Добавить сеть
        addArgs = ['wpa_cli', '-i', 'wlan0', 'add_network']
        net = sbp.check_output(addArgs).decode('utf-8')

        # Установить ssid сети
        addSsidArgs = ['wpa_cli', '-i', 'wlan0', 'set_network', net,
                       'ssid', "\""+ssid+"\""]
        if (sbp.check_output(addSsidArgs).decode('utf-8') != "OK\n"):
            LOG.error("Error occured during ssid set")
            raise ConnectionError

        # Установить ключ зашифрованной сети
        addPskArgs = ['wpa_cli', '-i', 'wlan0',
                      'set_network', net, 'psk', "\""+psk+"\""]
        if (sbp.check_output(addPskArgs).decode('utf-8') != "OK\n"):
            LOG.error("Error occured during psk set")
            raise ConnectionError

        # Активировать сеть
        enableArgs = ['wpa_cli', '-i', 'wlan0', 'enable_network', net]
        if (sbp.check_output(enableArgs).decode('utf-8') != "OK\n"):
            LOG.error("Error occured during network enable")
            raise ConnectionError

        # Компиляци регулярных выражений для поиска статуса подключения и ip
        regState = re.compile('\nwpa_state=(\w+)\n')
        regIp = re.compile('\nip_address=(\S+)\n')

        # Выполнять проверку статуса подключения 5 раз с перерывом в 3 сек
        for i in range(0, 5):
            LOG.info("Check state:")
            # Выполнить запрос статуса
            statusArgs = ['wpa_cli', '-i', 'wlan0', 'status']
            statusOutput = sbp.check_output(statusArgs).decode('utf-8')

            # Искать строку wpa_state
            match = regState.search(statusOutput)

            # Если нашли строку wpa_state
            if match is not None:
                state = match.group(1)

            # Если подключение выполнено
            if state == "COMPLETED":
                # Выполнять запрос статуса для выявления ip в сети
                # 10 раз с интервалом в 1 сек
                for j in range(0, 10):
                    # Статус
                    statusOutput = sbp.check_output(statusArgs).decode('utf-8')
                    # Искать ip в ответе
                    match = regIp.search(statusOutput)
                    # Если нашли
                    if match is not None:
                        # Сохранить и выйти из цикла
                        ip = match.group(1)
                        break
                    if (j == 9):
                        # Если за 10 попыток ip не найден
                        LOG.error("Error occured during ip check")
                        raise ConnectionError
                    sleep(1)

                # Сохранить конфигурацию
                saveArgs = ['wpa_cli', '-i', 'wlan0', 'save_config']
                saveOut = sbp.check_output(saveArgs).decode('utf-8')
                if saveOut == "OK\n":
                    LOG.info("Successufully connected with %s, ip: %s"
                             % (ssid, ip))
                    # Если все прошло успешно вывести ответ
                    output = {
                        "status": "OK",
                        "message": "Connection",
                        "payload":
                            {
                                "ssid": ssid,
                                "state": state,
                                "ip": ip,
                                "message": ""
                            }
                    }
                    break
                else:
                    LOG.error("Error occured during config save")
                    raise ConnectionError

            # Если не нашли статус за 5 попыток
            if i == 4:
                LOG.error("Error occured during status check")
                raise ConnectionError
            sleep(5)

    # Обработка исключений
    except Exception as e:
        LOG.error("Error during add_network")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Connection",
            "payload": None
        }
    return output
