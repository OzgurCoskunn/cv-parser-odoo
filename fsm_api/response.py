# -*- coding: utf-8 -*-

def Response200(code='', data={}):
    return '200', data


class Response400(Exception):
    status, reason, code = None, None, None
    def __init__(self, code, reason=None):
        super().__init__(code, reason)
        self.status = '400'
        self.reason = reason
        self.code = code


class Response401(Exception):
    status, reason, code = None, None, None
    def __init__(self, code, reason=None):
        super().__init__(code, reason)
        self.status = '401'
        self.reason = reason
        self.code = code


class Response403(Exception):
    status, reason, code = None, None, None
    def __init__(self, code, reason=None):
        super().__init__(code, reason)
        self.status = '403'
        self.reason = reason
        self.code = code


class Response404(Exception):
    status, reason, code = None, None, None
    def __init__(self, code, reason=None):
        super().__init__(code, reason)
        self.status = '404'
        self.reason = reason
        self.code = code


class Response422(Exception):
    status, reason, code, detail = None, None, None, []
    def __init__(self, code, detail, reason=None):
        super().__init__(code, reason)
        self.status = '422'
        self.reason = reason
        self.detail = detail
        self.code = code


class Response500(Exception):
    status, reason, code = None, None, None
    def __init__(self, code, reason=None):
        super().__init__(code, reason)
        self.status = '500'
        self.reason = reason
        self.code = code
