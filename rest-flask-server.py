#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin
import subprocess as sbp
import re
from time import sleep

# ============================= LOGS ============================= #
# Модуль для определения абсолютного пути
import os
# import sys
# Модуль логгер
import logging
from logging.handlers import TimedRotatingFileHandler

# Абсолютный путь к исполняемому скрипту
ROOT = os.path.dirname(os.path.abspath(__file__))

# Путь к файлу лога
LOG_FILE = os.path.join(ROOT, 'logs/flask-server.log')

LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

RFH = TimedRotatingFileHandler(LOG_FILE,
                               when="D",
                               interval=1,
                               backupCount=5)
RFH.setLevel(logging.DEBUG)

SH = logging.StreamHandler()
SH.setLevel(logging.DEBUG)

FORMATTER = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
RFH.setFormatter(FORMATTER)
SH.setFormatter(FORMATTER)

LOG.addHandler(SH)
LOG.addHandler(RFH)

# ============================= FLASK ============================= #
app = Flask(__name__, static_url_path="")
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/status', methods=['GET'])
@cross_origin()
def getStatus():
    LOG.info("Got status")
    args = ['wpa_cli', '-i', 'wlan0', 'status']
    try:
        statusOutput = str(sbp.check_output(args)).split("\n")
        status = {}
        for line in statusOutput[:len(statusOutput)-1]:
            prop, val = line.split("=")
            status[prop] = val
        response = {
            "status": "OK",
            "message": "Status service.",
            "payload": status
        }
    except Exception as e:
        LOG.error("Error occured during status check")
        LOG.error(e)
        response = {
            "status": "FAIL",
            "message": "Status service.",
            "payload": None
        }
    return jsonify(response)


@app.route('/scan', methods=['GET'])
@cross_origin()
def scan():
    LOG.info("Got scan")
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
                    "Flags": div_line[3],
                    "Ssid": div_line[4],
                }
                listNetworks[div_line[4]] = props
            response = {
                "status": "OK",
                "message": "Status service.",
                "payload": listNetworks
            }
    except Exception as e:
        LOG.error("Error occured during scan")
        LOG.error(e)
        response = {
            "status": "FAIL",
            "message": "Networks",
            "payload": None
        }
    return jsonify(response)


@app.route('/disconnect', methods=['GET'])
@cross_origin()
def disconnect():
    LOG.info("Got disconnect")
    disconnect = {
        "status": "OK",
        "message": "Disconnect service.",
        "payload": ""
        }
    return jsonify({'disconnect': disconnect})

class ConnectionError(Exception):
    """docstring for ConnectionError."""
    def __init__(self):
        super(ConnectionError, self).__init__()
        self.msg = "Error during establishing connection"
    def __str__(self):
        return self.msg


@app.route('/connect', methods=['POST'])
@cross_origin()
def connect():
    LOG.info("Got connect")
    if not request.json or 'ssid' not in request.json:
        abort(400)
    creds = request.get_json()
    ssid = creds['ssid'].encode('utf-8')
    psk = creds['psk'].encode('utf-8')
    connect = {}
    state = ""
    ip = ""

    try:
        addArgs = ['wpa_cli', '-i', 'wlan0', 'add_network']
        net = str(sbp.check_output(addArgs))

        addSsidArgs = ['wpa_cli', '-i', 'wlan0',
                        'set_network', net, 'ssid', "\""+ssid+"\""]
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

            if match != None:
                state = match.group(1)

            if state == "COMPLETED":
                for j in range(0, 10):
                    statusOutput = sbp.check_output(statusArgs)
                    match = regIp.search(statusOutput)
                    if match != None:
                        ip = match.group(1)
                        break
                    if (j == 9):
                        LOG.error("Error occured during ip check")
                        raise ConnectionError

                saveArgs = ['wpa_cli', '-i', 'wlan0', 'save_config']
                saveOut = sbp.check_output(saveArgs)
                if saveOut == "OK\n":
                    connect = {
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
                sleep(1)

            if i == 4:
                LOG.error("Error occured during status check")
                raise ConnectionError
            sleep(3)

        #
    except Exception as e:
        LOG.error("Error during add_network")
        raise(e)
        connect = {
            "status": "FAIL",
            "message": "Connection",
            "payload": None
        }
    return jsonify({'connect': connect})


if __name__ == '__main__':
    LOG.info("Entered main")
    app.run(debug=True)
