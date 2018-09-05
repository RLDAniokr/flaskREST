#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
import sqlite3
import logging

log = logging.getLogger(__name__)


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

getGroupNames():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_group = ''' SELECT DISTINCT group_name FROM sencors  '''
        cursor.execute(sql_group)
        results = cursor.fetchall()
        log.info(results)

def getSencorsSettings():
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql = ''' SELECT * FROM sencors  '''
        cursor.execute(sql)
        results = cursor.fetchall()
        log.info(results)

def newSencorSettings(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_ins = ''' INSERT INTO sencors(id, type, gr_name, name) VALUES (?,?,?,?)  '''
        cursor.execute(sql_ins, sencor)

def editSencor(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_upd = ''' UPDATE sencors SET gr_name = ? , name = ? WHERE id = ? AND type = ?  '''
        cursor.execute(sql_upd, upd_sencor)

def deleteSencor(sencor):
    with sqlite3.connect('rlda.db') as db:
        cursor = db.cursor()
        sql_del = ''' DELETE FROM sencors WHERE id = ? AND type = ?  '''
        cursor.execute(sql_del, del_sencor)


def editDevice(self, device):
    pass

def getDevicesSettings(self):
    pass
