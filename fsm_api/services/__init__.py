# -*- coding: utf-8 -*-

import json
import datetime
from odoo import _
from odoo.tools.safe_eval import _BUILTINS
from odoo.addons.fsm import TaskError
from ..response import Response200, Response400, Response401, Response403, Response404, Response422, Response500

NAMESPACE = {
    '__builtins__': {
        **_BUILTINS,
        '_': _,
        'json': json,
        'datetime': datetime,
        'TaskError': TaskError,
        'Response200': Response200,
        'Response400': Response400,
        'Response401': Response401,
        'Response403': Response403,
        'Response404': Response404,
        'Response422': Response422,
        'Response500': Response500,
    }
}
PROXY = {}
SPEC = {}

PARAMTYPE = [
    ('str', 'string'),
    ('int', 'integer'),
    ('float', 'float'),
    ('bool', 'boolean'),
    ('byte', 'byte'),
    ('date', 'date'),
    ('datetime', 'datetime'),
    ('list', 'array'),
    ('dict', 'object'),
]
PARAMTYPEMAP = dict(PARAMTYPE)

RESPONSETYPE = [
    ('200', '200 OK'),
    ('400', '400 Bad Request'),
    ('401', '401 Unauthorized'),
    ('403', '403 Forbidden'),
    ('404', '404 Not Found'),
    ('422', '422 Unprocessable Content'),
    ('500', '500 Internal Server Error'),
]

from . import rest
from . import soap