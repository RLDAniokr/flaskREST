#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import pyrebase

from time import sleep, time
import threading

from .sql import getFirebaseCredentials, getFirebaseConfig

import logging

log = logging.getLogger(__name__)

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


# Todo: make it singleton
#@singleton
class fireBase():
        def __init__(self):
                creds = getFirebaseCredentials()

                self.email = creds['email']
                self.password = creds['password']
                config = getFirebaseConfig()

                firebase = pyrebase.initialize_app(config)
                self.db = firebase.database()

                self.auth = firebase.auth()
                # Todo: try/catch w/ del or exception or some stuff
                self.user = self.auth.sign_in_with_email_and_password(self.email, self.password)
                self.user = self.auth.refresh(self.user['refreshToken'])
                self.uid = self.user['userId']
                self.root = lambda dir: self.db.child('users').child(self.uid).child(dir)
                self.token = self.user['idToken']

                self.last_token_upd = time()

                log.debug("Object initialized")

                #self.device_thread = self.root('devices').stream(self.ds_handler, self.token)


        def update_sencor_value(self, sencor):
                """ Update value of sencor on firebase cloud db """
                self.root(sencor.group_name).child("sencors").update({sencor.name:  sencor.value}, self.token)

        def delete_sencor(self, sencor):
            """ Delete sencor from db """
            self.root(sencor.group_name).child("sencors").child(sencor.name).remove(self.token)

        def update_device_value(self, device):
                """ Update value of device on firebase cloud db """
                self.root(device.group_name).child("devices").update({device.name:  device.value}, self.token)

        def delete_device(self, device):
            """ Delete device from db """
            self.root(device.group_name).child("sencors").child(device.name).remove(self.token)

        def upd_token(self):
                __t_diff = time() - self.last_token_upd
                if __t_diff > 3300:
                        log.info("Token expired")
                        self.user = self.auth.refresh(self.user['refreshToken'])
                        self.token = self.user['idToken']
                        self.last_token_upd = time()
