#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
import sqlite3
import logging

log = logging.getLogger(__name__)


# ======= Firebase ======= #
def getFirebaseCredentials():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __getEmailSQL = "SELECT * FROM fbSettings WHERE keyName='email'"
        cursor.execute(__getEmailSQL)
        email = cursor.fetchone()[1]

        __getPasswordSQL = "SELECT * FROM fbSettings WHERE keyName='password'"
        cursor.execute(__getPasswordSQL)
        password = cursor.fetchone()[1]

        creds = {'email': email, 'password': password}
        return creds

def setFirebaseCredentials(email, password):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __setEmailSQL = """ UPDATE fbSettings SET value = ? WHERE id = 'email' """
        cursor.execute(__setEmailSQL, email)

        __setPasswordSQL = """ UPDATE fbSettings SET value = ? WHERE id = 'password' """
        cursor.execute(__setPasswordSQL, password)

def getFirebaseConfig():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        __getFBconfSQL = "SELECT * FROM fbSettings WHERE keyName!='email' AND keyName!='password'"
        cursor.execute(__getFBconfSQL)
        __confTuple = cursor.fetchall()
        settings = {}
        for line in __confTuple:
            settings[line[0]] = line[1]
        return settings

# ======= Groups ======= #

def getGroupNames():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_group = ''' SELECT DISTINCT gr_name FROM sencors  '''
        cursor.execute(sql_group)
        results = cursor.fetchall()
        # TODO: get and append form devices
        return results

# ======= Sencors ======= #

def getSencorsSettings():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql = ''' SELECT * FROM sencors  '''
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

def newSencorSettings(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_ins = ''' INSERT INTO sencors(id, type, gr_name, name) VALUES (?,?,?,?)  '''
        cursor.execute(sql_ins, sencor)

def editSencor(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd = ''' UPDATE sencors SET gr_name = ? , name = ? WHERE id = ? AND type = ?  '''
        cursor.execute(sql_upd, sencor)

def deleteSencor(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_del = ''' DELETE FROM sencors WHERE id = ? '''
        cursor.execute(sql_del, sencor)

# ======= Devices ======= #

def getDevicesSettings():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql = ''' SELECT * FROM devices  '''
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

def newDeviceSettings(device):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_ins = ''' INSERT INTO devices(id, type, gr_name, name) VALUES (?,?,?,?)  '''
        cursor.execute(sql_ins, device)

def editDevice(device):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd = ''' UPDATE devices SET gr_name = ? , name = ? WHERE id = ? AND type = ?  '''
        cursor.execute(sql_upd, device)

def deleteDevice(device):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_del = ''' DELETE FROM devices WHERE id = ? '''
        cursor.execute(sql_del, device)
