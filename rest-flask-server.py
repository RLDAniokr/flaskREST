#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin
import subprocess

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
def get_status():
    LOG.info("Got status")
    status = {
        "status":"OK",
        "message":"status",
        "payload": {
                "address":"b8:27:eb:c4:c4:fd",
                "bssid":"08:60:6e:ba:82:f9",
                "freq":"2412",
                "group_cipher":"CCMP",
                "id":"0",
                "ip_address":"10.10.11.201",
                "key_mgmt":"WPA2-PSK",
                "mode":"station",
                "p2p_device_address":"fe:65:c3:f2:86:eb",
                "pairwise_cipher":"CCMP",
                "ssid":"ASUS_Guest1",
                "uuid":"f84b0928-9870-5917-bc6a-8d0a57ba4350",
                "wpa_state":"COMPLETED"
                }
            }
    return jsonify({'status': status})

@app.route('/scan', methods=['GET'])
@cross_origin()
def scan():
    LOG.info("Got scan")
    networks = {
        "status":"OK",
        "message":"Networks",
        "payload":{
            "ASUS 10":
                {"bssid":"08:60:6e:ba:82:f8",
                "frequency":"2462",
                "signal_level":"-74",
                "flags":"[WPA2-PSK-CCMP][ESS]",
                "ssid":"ASUS 10"},
            "ASUS2":
                {"bssid":"08:60:6e:cc:47:68",
                "frequency":"2427",
                "signal_level":"-79",
                "flags":"[WPA2-PSK-CCMP][ESS]",
                "ssid":"ASUS2"},
            "ASUS_Guest1":
                {"bssid":"08:60:6e:ba:82:f9",
                "frequency":"2462",
                "signal_level":"-74",
                "flags":"[WPA2-PSK-CCMP][ESS]",
                "ssid":"ASUS_Guest1"},
            "CityHall":
                {"bssid":"2c:ab:25:78:a4:d6",
                "frequency":"2437",
                "signal_level":"-90",
                "flags":"[WPA-PSK-CCMP+TKIP][WPA2-PSK-CCMP+TKIP][ESS]",
                "ssid":"CityHall"},
            "CityHall_2":
                {"bssid":"48:5b:39:e7:45:13",
                "frequency":"2437",
                "signal_level":"-94",
                "flags":"[WPA2-PSK-CCMP+TKIP][ESS]",
                "ssid":"CityHall_2"},
            "DENISENKO":
                {"bssid":"98:de:d0:cd:d6:5c",
                "frequency":"2457",
                "signal_level":"-89",
                "flags":"[WPA2-PSK-CCMP][WPS][ESS]",
                "ssid":"DENISENKO"},
            }
        }
    return jsonify({'networks': networks})

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

@app.route('/exec', methods=['GET'])
@cross_origin()
def execute():
    LOG.info("Got exec")
    args = ['assoc', '.API']
    try:
        ex = str(subprocess.check_output(args, shell=True))
    except Exception as e:
        ex = "FCK"
        LOG.error(e)

    return jsonify({'ex': ex})

if __name__ == '__main__':
    LOG.info("Entered main")
    app.run(debug=True)
