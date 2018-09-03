#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import pyrebase

from random import randint
from time import sleep, time
import threading

import sql

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
@singleton
class fireBase():
        def __init__(self):
                creds = sql.getFBcreds()

                self.email = creds['email']
                self.password = creds['password']

                ###
                #config = {
                #       'apiKey': "AIzaSyD0S98C7BpeiMvMc-KN4sOTnWN4nikCNDc",
                #       'authDomain': "test-firebasse-prj.firebaseapp.com",
                #       'databaseURL': "https://test-firebasse-prj.firebaseio.com",
                #       'projectId': "test-firebasse-prj",
                #       'storageBucket': "test-firebasse-prj.appspot.com",
                #       'messagingSenderId': "324013377533"
                #}
                
                config = sql.getFBsettings()

                firebase = pyrebase.initialize_app(config)
                self.db = firebase.database()

                self.auth = firebase.auth()
                # Todo: try/catch w/ del or exception or some stuff
                self.user = self.auth.sign_in_with_email_and_password(self.email, self.password)
                self.user = self.auth.refresh(self.user['refreshToken'])
                uid = self.user['userId']
                self.root = lambda dir: self.db.child('users').child(uid).child(dir)
                self.token = self.user['idToken']

                self.last_token_upd = time()
                self.auto_upd = threading.Thread(target=self.auto_upd_token)
                self.auto_upd.daemon = True
                self.auto_upd.start()

                log.debug("Object initialized")

                self.device_thread = self.root('devices').stream(self.ds_handler, self.token)


        def auto_upd_token(self):
                """ Update auth token """
                while True:
                        __t_diff = time() - self.last_token_upd
                        if __t_diff > 3300:
                                log.info("Token expired")
                                self.user = self.auth.refresh(self.user['refreshToken'])
                                self.token = self.user['idToken']
                                self.last_token_upd = time()
                                self.device_thread.close()
                                self.device_thread = self.root('devices').stream(self.ds_handler, self.token)

        def write_snc(self, snc_name):
                """ Write random data to DB/root/snc_N """
                new_data = str(randint(0, 30)) + ' cel. deg.'
                self.root("sencors").update({snc_name: new_data}, self.token)
                log.info("Data has sent %s:%s" %(snc_name, new_data))

        def snc_loop(self):
                try:
                        while True:
                                self.write_snc("t_h")
                                self.write_snc("t_k")
                                sleep(5)
                except KeyboardInterrupt:
                        log.info("That's all")

        def ds_handler(self, message):
                log.info("Attention! Data arrived")
                log.info("%s: %s" % (message['path'], message['data']))
