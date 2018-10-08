#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin

# Кастомный модуль для работы с wpa_cli (в корневой директории)
from wpa_commands import wpa_status, wpa_scan, wpa_connect, wpa_disconnect

from rpi.rpi import rpiHub

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
RFH.setLevel(logging.INFO)

SH = logging.StreamHandler()
SH.setLevel(logging.INFO)

format = '%(asctime)s - %(threadName)s  - %(levelname)s - %(message)s'
FORMATTER = logging.Formatter(format)
RFH.setFormatter(FORMATTER)
SH.setFormatter(FORMATTER)

LOG.addHandler(SH)
LOG.addHandler(RFH)

# ======================== Raspberry Core ========================= #
rpiHub = rpiHub()

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
    ssid = creds['ssid']
    # Выделение psk
    psk = creds['psk']

    response = {}
    response = wpa_connect(ssid, psk)
    return jsonify(response)


@app.route('/group', methods=['GET'])
@cross_origin()
def get_groups():
    """ Получение списка имен групп """
    LOG.info("Got connect")
    response = rpiHub.get_groups()
    return jsonify(response)


@app.route('/group/<group_name>', methods=['GET', 'POST', 'DELETE'])
@cross_origin()
def group(group_name):
    """
        @GET: Получение имен датчиков и устройств группы <group_name>
        @POST: Создание новой группы с именем <group_name>
        @DELETE: Удаление группы <group_name>
    """
    LOG.info("Got connect")
    response = {}
    if request.method == 'GET':
        response = rpiHub.get_group_info(group_name)
    if request.method == 'POST':
        response = rpiHub.add_group(group_name)
    elif request.method == 'DELETE':
        response = rpiHub.remove_group(group_name)
    return jsonify(response)


@app.route('/sencor', methods=['POST', 'PUT', 'DELETE'])
@cross_origin()
def sencor():
    """
        @POST: создание нового датчика
        @PUT: редактирование имени и группы датчика
        @DELETE: удаление датчика
        input: json {snc_id(int), snc_type(str), snc_group(str), snc_name(str)}
    """
    LOG.info("Got sencor")
    response = {}
    if not request.json:
        LOG.info("NO JSON")
        abort(400)
    elif 'snc_id' not in request.json or 'snc_type' not in request.json:
        abort(400)

    # Забрать json
    config = request.get_json()
    snc_id = int(config['snc_id'])
    snc_type = config['snc_type']

    if request.method != 'DELETE':
        snc_group = config['snc_group']
        snc_name = config['snc_name']

    if request.method == 'POST':
        response = rpiHub.add_snc(snc_type=snc_type,
                                  snc_id=snc_id,
                                  snc_group=snc_group,
                                  snc_name=snc_name)
    elif request.method == 'PUT':
        response = rpiHub.edit_snc(snc_type=snc_type,
                                   snc_id=snc_id,
                                   new_snc_group=snc_group,
                                   new_snc_name=snc_name)
    elif request.method == 'DELETE':
        response = rpiHub.remove_snc(snc_id=snc_id, snc_type=snc_type)
    return jsonify(response)


@app.route('/device', methods=['POST', 'PUT', 'DELETE'])
@cross_origin()
def device():
    """
        @POST: создание нового устройства
        @PUT: редактирование имени и группы устройства
        @DELETE: удаление устройства
        input: json {dvc_id(int), dvc_type(str), dvc_group(str), dvc_name(str)}
    """
    LOG.info("Got device")
    response = {}
    if not request.json:
        abort(400)
    elif 'dvc_id' not in request.json or 'dvc_type' not in request.json:
        abort(400)

    # Забрать json
    config = request.get_json()
    dvc_id = int(config['dvc_id'])
    dvc_type = config['dvc_type']

    # add info for relay
    ch0name = None
    ch1name = None

    if request.method != 'DELETE':
        dvc_group = config['dvc_group']
        dvc_name = config['dvc_name']
        if dvc_type == 'Relay':
            ch0name = config['ch0name']
            ch1name = config['ch1name']

    if request.method == 'POST':
        response = rpiHub.add_dvc(dvc_type=dvc_type,
                                  dvc_id=dvc_id,
                                  dvc_group=dvc_group,
                                  dvc_name=dvc_name,
                                  ch0name=ch0name,
                                  ch1name=ch1name)
    elif request.method == 'PUT':
        response = rpiHub.edit_dvc(dvc_type=dvc_type,
                                   dvc_id=dvc_id,
                                   new_dvc_group=dvc_group,
                                   new_dvc_name=dvc_name)
    elif request.method == 'DELETE':
        response = rpiHub.remove_dvc(dvc_id=dvc_id, dvc_type=dvc_type)
    return jsonify(response)


@app.route('/firebase', methods=['POST', 'PUT'])
@cross_origin()
def firebase_creds():
    """
        @POST: регистрация нового пользователя
        @PUT: редактирование email и пароля пользователя Firebase
        input: json {email(string), password(string)}
    """
    LOG.info("Got firebase")
    response = {}
    if not request.json:
        abort(400)
    elif 'email' not in request.json or 'password' not in request.json:
        abort(400)

    # Забрать json
    credentials = request.get_json()
    email = credentials['email']
    password = credentials['password']

    if request.method == 'POST':
        response = rpiHub.set_fb_creds(email, password)
    elif request.method == 'PUT':
        response = rpiHub.reset_fb_creds(email=email, password=password)
    return jsonify(response)


# Точка входа main
if __name__ == '__main__':
    LOG.info("Entered main")
    app.run(debug=False)
