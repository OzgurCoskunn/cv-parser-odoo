# -*- coding: utf-8 -*-

class TaskError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.traceback = ('', '', '')
        self.with_traceback(None)
        self.__cause__ = None
        self.loglevel = 20

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


class ReasonError(Exception):
    def __init__(self, message, action):
        super().__init__(message, action)
        self.message = message
        self.traceback = ('', '', '')
        self.with_traceback(None)
        self.__cause__ = None
        self.loglevel = 20

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


class AppointmentError(Exception):
    def __init__(self, message, action):
        super().__init__(message, action)
        self.message = message
        self.traceback = ('', '', '')
        self.with_traceback(None)
        self.__cause__ = None
        self.loglevel = 20

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


from . import controllers
from . import models
from . import wizards
