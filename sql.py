#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
import sqlite3
import logging

log = logging.getLogger(__name__)


class LocalDB(object):
    def __init__():
        self.db = sqlite3.connect('rlda.db')
        self.cursor = self.db.cursor()

    def getFirebaseCredentials(self):
        __getEmailSQL = "SELECT * FROM fbSettings WHERE keyName='email'"
        c.execute(__getEmailSQL)
        email = c.fetchone()[1]

        __getPasswordSQL = "SELECT * FROM fbSettings WHERE keyName='password'"
        c.execute(__getPasswordSQL)
        password = c.fetchone()[1]

        creds = {'email': email, 'password': password}
        return creds

    def getFirebaseConfig(self):
        __getFBconfSQL = "SELECT * FROM fbSettings WHERE keyName!='email' AND keyName!='password'"
        c.execute(__getFBconfSQL)
        __confTuple = c.fetchall()
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
