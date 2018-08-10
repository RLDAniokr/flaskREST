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


def wpa_status():
    output = {}
    args = ['wpa_cli', '-i', 'wlan0', 'status']
    try:
        statusOutput = str(sbp.check_output(args)).split("\n")
        status = {}
        for line in statusOutput[:len(statusOutput)-1]:
            prop, val = line.split("=")
            status[prop] = val
        output = {
            "status": "OK",
            "message": "Status service.",
            "payload": status
        }
    except Exception as e:
        LOG.error("Error occured during status check")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Status service.",
            "payload": None
        }
    return output


def wpa_scan():
    output = {}
    try:
        scanCommandArgs = ['wpa_cli', '-i', 'wlan0', "scan"]
        scanListArgs = ['wpa_cli', '-i', 'wlan0', "scan_results"]
        if (sbp.call(scanCommandArgs) == 0):
            sleep(1)
            tmp = str(sbp.check_output(scanListArgs)).split("\n")

            listNetworks = {}
            for line in tmp[1:len(tmp)-1]:
                div_line = line.split("\t")
                props = {
                    "bssid": div_line[0],
                    "frequency": div_line[1],
                    "SignalLevel": div_line[2],
                    "flags": div_line[3],
                    "ssid": div_line[4],
                }
                listNetworks[div_line[4]] = props
            output = {
                "status": "OK",
                "message": "Status service.",
                "payload": listNetworks
            }
    except Exception as e:
        LOG.error("Error occured during scan")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Networks",
            "payload": None
        }
    return output


def wpa_disconnect():
    output = {}
    try:
        dcArgs = ['wpa_cli', '-i', 'wlan0', 'disconnect']
        dcStatus = sbp.check_output(dcArgs)
        if dcStatus != "OK\n":
            LOG.error("Error during disconnect")
            raise DisconnectionError

        listArgs = ['wpa_cli', '-i', 'wlan0', 'list_networks']
        listNetworks = sbp.check_output(listArgs).split("\n")

        for network in listNetworks[1:len(listNetworks)-1]:
            networkId, _ = network.split("\t", 1)
            rmNetArgs = ['wpa_cli', '-i', 'wlan0', 'remove_network', networkId]
            rmNetOut = sbp.check_output(rmNetArgs)
            if rmNetOut != "OK\n":
                LOG.error("Error occured during network removal")
                LOG.error("Network id: %s" % networkId)
                raise DisconnectionError

        reasArgs = ['wpa_cli', '-i', 'wlan0', 'reassociate']
        reasStatus = sbp.check_output(reasArgs)
        if reasStatus != "OK\n":
            LOG.error("Error occured during network reassociate")
            raise DisconnectionError

        output = {
            "status": "OK",
            "message": "Disconnect service.",
            "payload": ""
        }

    except Exception as e:
        LOG.error("Error occured while disconnect")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Disconnect service.",
            "payload": ""
        }
    return output


def wpa_connect(ssid, psk):
    output = {}
    state = ""
    ip = ""
    wpa_disconnect()
    try:
        addArgs = ['wpa_cli', '-i', 'wlan0', 'add_network']
        net = str(sbp.check_output(addArgs))

        addSsidArgs = ['wpa_cli', '-i', 'wlan0', 'set_network', net,
                       'ssid', "\""+ssid+"\""]
        if (sbp.check_output(addSsidArgs) != "OK\n"):
            LOG.error("Error occured during ssid set")
            raise ConnectionError

        addPskArgs = ['wpa_cli', '-i', 'wlan0',
                      'set_network', net, 'psk', "\""+psk+"\""]
        if (sbp.check_output(addPskArgs) != "OK\n"):
            LOG.error("Error occured during psk set")
            raise ConnectionError

        enableArgs = ['wpa_cli', '-i', 'wlan0', 'enable_network', net]
        if (sbp.check_output(enableArgs) != "OK\n"):
            LOG.error("Error occured during network enable")
            raise ConnectionError

        regState = re.compile('\nwpa_state=(\w+)\n')
        regIp = re.compile('\nip_address=(\S+)\n')

        for i in range(0, 5):
            LOG.info("Check state:")
            statusArgs = ['wpa_cli', '-i', 'wlan0', 'status']
            statusOutput = sbp.check_output(statusArgs)

            match = regState.search(statusOutput)

            if match is not None:
                state = match.group(1)

            if state == "COMPLETED":
                for j in range(0, 10):
                    statusOutput = sbp.check_output(statusArgs)
                    match = regIp.search(statusOutput)
                    if match is not None:
                        ip = match.group(1)
                        break
                    if (j == 9):
                        LOG.error("Error occured during ip check")
                        raise ConnectionError
                    sleep(1)

                saveArgs = ['wpa_cli', '-i', 'wlan0', 'save_config']
                saveOut = sbp.check_output(saveArgs)
                if saveOut == "OK\n":
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

            if i == 4:
                LOG.error("Error occured during status check")
                raise ConnectionError
            sleep(3)

    except Exception as e:
        LOG.error("Error during add_network")
        LOG.error(e)
        output = {
            "status": "FAIL",
            "message": "Connection",
            "payload": None
        }
    return output
