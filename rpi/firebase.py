#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import pyrebase
from requests.exceptions import ConnectionError as ConnErr

from time import sleep, time
import threading
import logging

from . import sql

log = logging.getLogger(__name__)


def singleton(class_):
    """ Декоратор для класса-одиночки """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


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

        # Резервирование для объектов потока и обработчика статистики
        self.wd_stream = None
        self.wd_handler = None

        # Резервирование переменных дл времени последнего ответа и
        # пользовательского идентификатора
        self.last_token_upd = time()
        self.uid = ""

        # Если данные не пустые (Пользователь зарегистрировался)
        if self.email is not None and self.password is not None:
            log.info("GOT FB CREDS")
            self.is_auth = self.authorize(self.email, self.password)

        # TODO: set new thread for internet connection check
        # TODO: setup method for email approval
        # TODO: setup method for credentials reset

    def register_new_user(self, email, password):
        """ Зарегистрировать нового пользователя """
        try:
            # Отправить запрос на регистрацию нового пользователя
            self.auth.create_user_with_email_and_password(email, password)
            # Подождать регистрации на облаке
            sleep(2)
            # Записать данные в базу
            sql.setFirebaseCredentials(email, password)
            # Авторизоваться
            self.authorize(email, password)
            # Вернуть статус успешной регистрации
            return "OK"
        except Exception as e:
            # Обработка ошибки регистрации
            # TODO: Обработать статус наличия пользователя с указанной почтой
            log.error("Error during new user register")
            log.exception(e)
            return "FAIL"

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
            # Вывесть статус входа в лог
            log.info("Authorized")

            return True
        except Exception as e:
            # Внести ошибку в лог
            log.exception(e)
            log.info("Unauthorized")
            return False

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
            try:
                # Установить query-путь к данным датчика в облаке
                _group_dir = self.root.child('groups').child(sencor.group_name)
                _snc_dir = _group_dir.child("sencors")
                # Обновить данные в облаке
                _snc_dir.update(_data, self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                # Обработчик ошибки обновления
                log.error("Error occured while updating sencor value")
                log.exception(e)

    def delete_sencor(self, sencor):
        """ Удалить данные сенсора из облачной базы данных """
        if self.is_auth:
            try:
                # Установить query-путь к данным датчика в облаке
                _group_dir = self.root.child('groups').child(sencor.group_name)
                _snc_dir = _group_dir.child("sencors")
                # Удалить query-путь к данным датчика в облаке
                _snc_dir.child(sencor.name).remove(self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.error("Error occured while sencor delete")
                log.exception(e)

    def set_strm(self, handler, gr_name):
        """ Установить поток прослушки команд устройств угруппы """
        stream = None
        try:
            # Директория
            _dvc_dir = self.root.child('groups').child(gr_name).child('devices')
            # Экземпляр потока прослушки
            stream = _dvc_dir.stream(handler, stream_id=gr_name, token=self.token)
        except ConnErr as e:
            # Ошибка подключения, потеря интернет соединения
            self.is_auth = False
            log.error("Internet connection is lost")
            log.exception(e)
        except Exception as e:
            log.exception(e)

        return stream

    def update_device_value(self, device):
        """ Обновить данные устройства в облачной базе данных """
        if self.is_auth:
            _data = device.form_data()
            try:
                # Установить query-путь к данным устройства в облаке
                _group_dir = self.root.child('groups').child(device.group_name)
                _dvc_dir = _group_dir.child("devices")
                # Обновить данные устройства в облаке
                _dvc_dir.update(_data, self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.error("Error occured while updating device")
                log.exception(e)

    def delete_device(self, device):
        """ Удалить данные устройства из облачной базы данных """
        if self.is_auth:
            try:
                # Установить query-путь к данным устройства в облаке
                _group_dir = self.root.child('groups').child(device.group_name)
                _dvc_dir = _group_dir.child("devices")
                # Удалить query-путь к данным устройства в облаке
                _dvc_dir.child(device.name).remove(self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
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
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.error("Error occured while deleting group")
                log.exception(e)

    def update_time(self):
        """ Обновление UNIX-времени в топике последнего сообщения """
        # Данные (unixtime)
        __data = {"last_upd": time()}
        if self.is_auth:
            try:
                # Обновление данных в базе
                self.root.update(__data, self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.exception(e)

    def init_warden(self, handler=None):
        """ Метод инициализирования потока для статистики """
        if handler is not None:
            # Забрать обработчик, если он не сохранен
            self.wd_handler = handler

        try:
            # Установить экземпляр потока прослушки в корне директории /stats
            self.wd_stream = self.root.child('stats').stream(self.wd_handler,
                                                             stream_id="stats",
                                                             token=self.token)
            # Обновить статус статистики (Ожидание)
            self.update_stats(status="AWAIT")
        except ConnErr as e:
            # Ошибка подключения, потеря интернет соединения
            self.is_auth = False
            log.error("Internet connection is lost")
            log.exception(e)
        except Exception as e:
            log.exception(e)
            # TODO: XXX: return something?

    def update_stats(self, status=None, data=None):
        """ Метод обновления статуса и/или данных статистики """
        # Если обновляется статус
        if status:
            try:
                # Обновить значение статуса
                self.root.child('stats').update({'status': status}, self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.exception(e)
        # Если обновляются данные
        if data:
            try:
                # Установить query-путь к данным статистики
                __calc_path = self.root.child('stats').child('calcs')
                # Удалить старые данные
                __calc_path.remove(self.token)
                # Установить новые данные
                __calc_path.update(data, self.token)
            except ConnErr as e:
                # Ошибка подключения, потеря интернет соединения
                self.is_auth = False
                log.error("Internet connection is lost")
                log.exception(e)
            except Exception as e:
                log.exception(e)

    def read_stats(self):
        """ Метод чтения параметров подсчета статистики """
        # Начальные значения выходного словаря
        stats = {
            'id': "None",
            'date': "None"
        }
        try:
            # Корневой query-путь статистики
            __stats_root = self.root.child('stats')
            # Считать идентификатор датчика
            __raw_id = __stats_root.child('id').get(self.token).val()
            # Считать запрашиваемую дату
            __raw_date = __stats_root.child('date').get(self.token).val()
            # Записать считанные значения в выходной словарь
            stats['id'] = __raw_id
            stats['date'] = __raw_date
        except ConnErr as e:
            # Ошибка подключения, потеря интернет соединения
            self.is_auth = False
            log.error("Internet connection is lost")
            log.exception(e)
        except Exception as e:
            log.exception(e)

        # Вернуть выходной словарь
        return stats

    def upd_token(self, group_list, handler):
        """ Обновить токен доступа """
        # Проверка подключения
        if not self.is_auth:
            if self.email is not None and self.password is not None:
                self.is_auth = self.authorize(self.email, self.password)
                if self.is_auth:
                    self.wd_stream = self.init_warden()
                    for group in group_list:
                        try:
                            # Закрыть поток
                            group.dvc_stream.close()
                        except AttributeError:
                            # NOTE: Иногда закрытие стрима может вывалится с
                            # ошибкой аттрибута (косяк библиотеки)
                            pass
                        # Установить query-путь для устройств группы
                        _gr = self.root.child('groups').child(group.name)
                        _dvc_dir = _gr.child("devices")

                        # Создать новый поток для прослушки канала устройств
                        group.dvc_stream = _dvc_dir.stream(handler,
                                                           stream_id=group.name,
                                                           token=self.token)
                        # Установить время последнего обновления токена
                        self.last_token_upd = time()
                        return

        # Разница времени между текущим моментом и последним обновлением токена
        # NOTE: токен работает не больше часа
        __t_diff = time() - self.last_token_upd
        # Если после последнего обновления токена прошло больше 55 минут
        if __t_diff > 3300 and self.is_auth:
            log.info("Token expired")
            try:
                # Обновить токен
                self.user = self.auth.refresh(self.user['refreshToken'])
                # Выделить токен
                self.token = self.user['idToken']

                # Закрыть поток чтения команд для сбора статистики
                try:
                    self.wd_stream.close()
                except AttributeError:
                    pass
                # Открыть новый поток прослушки команд для статистики
                self.wd_stream = self.init_warden()

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
                    _gr = self.root.child('groups').child(group.name)
                    _dvc_dir = _gr.child("devices")

                    # Создать новый поток для прослушки канала устройств группы
                    group.dvc_stream = _dvc_dir.stream(handler,
                                                       stream_id=group.name,
                                                       token=self.token)
                    # Установить время последнего обновления токена
                    self.last_token_upd = time()
            except Exception as e:
                # Обработка исключения
                log.error("Error occured while updating token")
                log.error(e)
