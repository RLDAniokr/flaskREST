#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
import sqlite3
import logging

log = logging.getLogger(__name__)


# ======= Firebase ======= #


def getFirebaseCredentials():
    """ Запрос регистрационных данных для входа в Firebase  """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __getEmailSQL = """ SELECT * FROM fbSettings
                            WHERE keyName='email' """
        cursor.execute(__getEmailSQL)
        email = cursor.fetchone()[1]

        __getPasswordSQL = """ SELECT * FROM fbSettings
                               WHERE keyName='password' """
        cursor.execute(__getPasswordSQL)
        password = cursor.fetchone()[1]

        creds = {'email': email, 'password': password}
        return creds


def setFirebaseCredentials(email, password):
    """ Установка регистрационных данных для входа в Firebase """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __setEmailSQL = """ UPDATE fbSettings
                            SET val = ?
                            WHERE keyName = 'email' """
        cursor.execute(__setEmailSQL, (email,))

        __setPasswordSQL = """ UPDATE fbSettings
                               SET val = ?
                               WHERE keyName = 'password' """
        cursor.execute(__setPasswordSQL, (password,))


def getFirebaseConfig():
    """ Запрос настроек базы для Firebase """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __getFBconfSQL = """ SELECT * FROM fbSettings
                             WHERE keyName!='email' AND keyName!='password' """
        cursor.execute(__getFBconfSQL)
        __confTuple = cursor.fetchall()
        settings = {}
        for line in __confTuple:
            settings[line[0]] = line[1]
        return settings

# ======= Groups ======= #


def getGroupNames():
    """ Запрос имен групп """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        # NOTE: Запросить имена групп из таблиц датчиков и устройств
        sql_group = """ SELECT DISTINCT gr_name FROM sencors
                        UNION
                        SELECT DISTINCT gr_name FROM devices """
        cursor.execute(sql_group)
        results = cursor.fetchall()
        # TODO: get and append form devices
        return results

# ======= Sencors ======= #


def getSencorsSettings():
    """ Запрос настроек датчиков """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql = """ SELECT * FROM sencors  """
        cursor.execute(sql)
        results = cursor.fetchall()
        return results


def newSencorSettings(sencor):
    """ Внесение нового датичка """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_ins = """ INSERT INTO sencors(id, type, gr_name, name)
                      VALUES (?,?,?,?)  """
        cursor.execute(sql_ins, sencor)


def editSencor(sencor):
    """ Обновление настроек датчика """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd = """ UPDATE sencors
                      SET gr_name = ? , name = ?
                      WHERE id = ? """
        cursor.execute(sql_upd, (sencor))


def deleteSencor(sencor):
    """ Удаление датчика """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_del = """ DELETE FROM sencors WHERE id = ? """
        cursor.execute(sql_del, (sencor,))

# ======= Devices ======= #


def getDevicesSettings():
    """ Запрос настроек устройств """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql = """ SELECT * FROM devices  """
        cursor.execute(sql)
        results = cursor.fetchall()
        return results


def newDeviceSettings(device):
    """ Внесение нового устройства """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_ins = """ INSERT INTO devices(id, type, gr_name, name,
                      ch0name, ch1name, last_val)
                      VALUES (?,?,?,?,?,?,?)  """
        cursor.execute(sql_ins, device)


def editDevice(device):
    """ Изменение настроек устройства """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd = """ UPDATE devices
                       SET gr_name = ? , name = ? , ch0name = ? , ch1name = ?
                       WHERE id = ? """
        cursor.execute(sql_upd, device)


def saveLast(device):
    """ Сохранение последнего состояния реле """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd_lv = """ UPDATE devices
                       SET last_val = ?
                       WHERE id = ? """
        cursor.execute(sql_upd_lv, device)


def deleteDevice(device):
    """ Удаление устройства """
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_del = """ DELETE FROM devices WHERE id = ? """
        cursor.execute(sql_del, (device,))
