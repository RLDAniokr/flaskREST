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

def getSencorsSettings(self):
    pass

def getDevicesSettings(self):
    pass

def editSencor(self, sencor):
    pass

def editDevice(self, device):
    pass
