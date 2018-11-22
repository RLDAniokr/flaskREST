#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import pyrebase
import requests

from time import sleep, time
import threading

from . import sql

import logging

log = logging.getLogger(__name__)


def singleton(class_):
    """ Декоратор для класса-одиночки """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

# TODO: # XXX: # NOTE: change CRUD groups path
@singleton
class fireBase():
    """
        Класс объекта-одиночки для работы с облачной базой данных
        Google Firebase
    """
    def __init__(self):
        # Общая конфигурация firebase
        config = sql.getFirebaseConfig()
        # Инициализировать приложение
        firebase = pyrebase.initialize_app(config)
        # Экземпляр базы данных
        self.db = firebase.database()
        # Экземпляр аутентификации
        self.auth = firebase.auth()
        # Флаги для проверки состояния подключения
        self.is_auth = False
        self.prev_inet_state = False

        # Забрать данные из базы
        creds = sql.getFirebaseCredentials()
        self.email = creds['email']
        self.password = creds['password']

        # Если данные не пустые (Пользователь зарегистрировался)
        if self.email is not None and self.password is not None:
            log.info("GOT FB CREDS")
            self.authorize(self.email, self.password)

        # TODO: set new thread for internet connection check

    def register_new_user(self, email, password):
        """ Зарегистрировать нового пользователя """
        try:
            # Отправить запрос на регистрацию нового пользователя
            self.auth.create_user_with_email_and_password(email, password)
            # Подождать регистрации на облаке
            sleep(2)
        except Exception as e:
            # Обработка ошибки регистрации
            # TODO: Обработать статус наличия пользователя с указанной почтой
            log.error("Error during new user register")
            log.exception(e)
            return "FAIL"
        finally:
            # Записать данные в базу
            sql.setFirebaseCredentials(email, password)
            # Авторизоваться
            self.authorize(email, password)
            # Вернуть статус успешной регистрации
            return "OK"

    def check_connection(self):
        """ Worker-метод для проверки интернет соединения """
        while True:
            # URL для пинга
            __url = 'http://www.google.com'
            # Таймаут ответа от URL
            __timeout = 3
            try:
                # Выполнить запрос на заданный URl
                _ = requests.get(__url, timeout=__timeout)
                # Если при предыдущей итерации соединения не было
                if not self.prev_inet_state:
                    # Провести повторную авторизацию
                    self.authorize()
                # Указать состояние для следующей итерации
                self.prev_inet_state = True
            except requests.ConnectionError:
                # Поймать исключение проблемы с соединением
                # Установить значение для следующей итерации
                self.prev_inet_state = False
                # Обнулить флаг аутэнтификации
                self.is_auth = False

    def authorize(self, email, pswd):
        """ Авторизоваться в системе по почте и паролю """
        try:
            # Войти в системе по паре email+пароль
            self.user = self.auth.sign_in_with_email_and_password(email, pswd)
            # Обновить токен доступа
            self.user = self.auth.refresh(self.user['refreshToken'])
            # Выделить uid пользователя
            self.uid = self.user['userId']
            # Выделить токен доступа
            self.token = self.user['idToken']

            # Зафиксировать время последнего обновления токена
            self.last_token_upd = time()
            # Установить флаг фхода в систему
            self.is_auth = True
            # Вывесть статус входа в лог
            log.info("Authorized")
        except Exception as e:
            # Установить флаг фхода в систему
            self.is_auth = False
            # Внести ошибку в лог
            log.exception(e)
            log.info("Unauthorized")

    @property
    def root(self):
        """
            Вычисляемое свойство объекта: query-путь в корневую
            директорию пользователя. Read-only
        """
        return self.db.child('users').child(self.uid)

    def update_sencor_value(self, sencor):
        """ Обновить данные датчика в облачной базе данных """
        # Если установлен флаг входа
        if self.is_auth:
            _data = sencor.form_data()
            # Установить query-путь к данным датчика в облаке
            _group_dir = self.root.child('groups').child(sencor.group_name)
            _snc_dir = _group_dir.child("sencors")
            try:
                # Обновить данные в облаке
                _snc_dir.update(_data, self.token)
            except Exception as e:
                # Обработчик ошибки обновления
                log.error("Error occured while updating sencor value")
                log.exception(e)

    def delete_sencor(self, sencor):
        """ Удалить данные сенсора из облачной базы данных """
        if self.is_auth:
            # Установить query-путь к данным датчика в облаке
            _group_dir = self.root.child('groups').child(sencor.group_name)
            _snc_dir =_group_dir.child("sencors")
            try:
                # Удалить query-путь к данным датчика в облаке
                _snc_dir.child(sencor.name).remove(self.token)
            except Exception as e:
                log.error("Error occured while sencor delete")
                log.exception(e)

    def set_strm(self, handler, gr_name):
        _dvc_dir = self.root.child('groups').child(gr_name).child('devices')
        stream = _dvc_dir.stream(handler, stream_id=gr_name, token=self.token)
        return stream

    def set_device_type(self, device):
        """ Метод установки типа устройства в fb """
        if self.is_auth:
            _data = {device.name + "/dvc_type": device.type}
            _group_dir = self.root.child('groups').child(device.group_name)
            _dvc_dir = _group_dir.child("devices")
            try:
                _dvc_dir.update(__data, self.token)
            except Exception as e:
                log.error("Error occured while device type set")
                log.exception(e)

    def update_device_value(self, device):
        """ Обновить данные устройства в облачной базе данных """
        if self.is_auth:
            _data = device.form_data()
            # Установить query-путь к данным устройства в облаке
            _group_dir = self.root.child('groups').child(device.group_name)
            _dvc_dir = _group_dir.child("devices")
            try:
                # Обновить данные устройства в облаке
                _dvc_dir.update(_data, self.token)
            except Exception as e:
                log.error("Error occured while updating device")
                log.exception(e)

    def delete_device(self, device):
        """ Удалить данные устройства из облачной базы данных """
        if self.is_auth:
            # Установить query-путь к данным устройства в облаке
            _group_dir = self.root.child('groups').child(device.group_name)
            _dvc_dir = _group_dir.child("devices")
            try:
                # Удалить query-путь к данным устройства в облаке
                _dvc_dir.child(device.name).remove(self.token)
            except Exception as e:
                # Обработка ошибки удаления
                log.error("Error occured while updating device")
                log.exception(e)

    def delete_group(self, group):
        """ Удалить группу из облачной базы данных """
        # Условный метод удаления группы
        # NOTE: если группа пустая, то в облаке она не отображается
        if self.is_auth:
            try:
                self.root.child('groups').child(group).remove(self.token)
            except Exception as e:
                log.error("Error occured while deleting group")
                log.exception(e)

    def update_time(self):
        """ Обновление UNIX-времени в топике последнего сообщения """
        __data = {"last_upd": time()}
        try:
            self.root.update(__data, self.token)
        except Exception as e:
            log.exception(e)

    def upd_token(self, group_list, handler):
        """ Обновить токен доступа """
        __t_diff = time() - self.last_token_upd
        # NOTE: токен работает не больше часа
        # Если после последнего обновления токена прошло больше 55 минут
        if __t_diff > 3300 and self.is_auth:
            log.info("Token expired")
            try:
                # Обновить токен
                self.user = self.auth.refresh(self.user['refreshToken'])
            except Exception as e:
                # Обработка исключения
                log.error("Error occured while updating token")
                log.error(e)
                return
            finally:
                # Выделить токен
                self.token = self.user['idToken']
                # Закрыть все текущие потоки прослушки команд устройствам
                for group in group_list:
                    try:
                        # Закрыть поток
                        group.dvc_stream.close()
                    except AttributeError:
                        # NOTE: Иногда закрытие стрима может вывалится с
                        # ошибкой аттрибута (косяк библиотеки)
                        pass
                    # Установить query-путь для устройств группы
                    _gr = self.root.child('groups').child(device.group_name)
                    _dvc_dir = _gr.child("devices")

                    # Создать новый поток для прослушки канала устройств группы
                    group.dvc_stream = _dvc_dir.stream(handler,
                                                       stream_id=group.name,
                                                       token=self.token)
                # Установить время последнего обновления токена
                self.last_token_upd = time()
