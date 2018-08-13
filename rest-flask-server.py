#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin

# Кастомный модуль для работы с wpa_cli (в корневой директории)
from wpa_commands import wpa_status, wpa_scan, wpa_connect, wpa_disconnect

# ============================= LOGS ============================= #
# Модуль для определения абсолютного пути
import os
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

FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
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
    """ Запрос статуса подключений """
    LOG.info("Got status")
    response = {}
    response = wpa_status()
    return jsonify(response)


@app.route('/scan', methods=['GET'])
@cross_origin()
def scan():
    """ Сканирование сети """
    LOG.info("Got scan")
    response = {}
    response = wpa_scan()
    return jsonify(response)


@app.route('/disconnect', methods=['GET'])
@cross_origin()
def disconnect():
    """ Разрыв соединения """
    LOG.info("Got disconnect")
    response = {}
    response = wpa_disconnect()

    return jsonify(response)


@app.route('/connect', methods=['POST'])
@cross_origin()
def connect():
    """ Подключение к заданной сети """
    LOG.info("Got connect")
    # Если тело не является json или нет ключа ssid вернуть 400
    if not request.json or 'ssid' not in request.json:
        abort(400)
    # Забрать json
    creds = request.get_json()
    # Выделение ssid
    ssid = creds['ssid'].encode('utf-8')
    # Выделение psk
    psk = creds['psk'].encode('utf-8')

    response = {}
    response = wpa_connect(ssid, psk)
    return jsonify(response)


# Точка входа main
if __name__ == '__main__':
    LOG.info("Entered main")
    app.run(debug=True)
