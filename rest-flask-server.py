#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin
import subprocess as sbp
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
app = Flask(__name__, static_url_path = "")
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)


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
                listNetworks[props[4]] = props
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
        "status":"OK",
        "message":"Disconnect service.",
        "payload": ""
        }
    return jsonify({'disconnect': disconnect})

@app.route('/connect', methods=['POST'])
@cross_origin()
def connect():
    LOG.info("Got connect")
    if not request.json or not 'title' in request.json:
        abort(400)
    LOG.debug(request)
    LOG.info("POST: ssid = ")
    connect = {
        "status":"OK",
        "message":"Connection",
        "payload":
            {
                "ssid":"ASUS_Guest1",
                "state":"COMPLETED",
                "ip":"10.10.11.201",
                "message":""
            }
        }
    return jsonify({'connect': connect})


if __name__ == '__main__':
    LOG.info("Entered main")
    app.run(debug=True)
