# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re

import werkzeug.routing
from apispec import BasePlugin
from werkzeug.routing import Map, Rule
from ..tools import ROUTING_DECORATOR_ATTR

# from flask-restplus
RE_URL = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")

DEFAULT_CONVERTER_MAPPING = {
    werkzeug.routing.UnicodeConverter: ("string", None),
    werkzeug.routing.IntegerConverter: ("integer", "int32"),
    werkzeug.routing.FloatConverter: ("number", "float"),
    werkzeug.routing.UUIDConverter: ("string", "uuid"),
}
DEFAULT_TYPE = ("string", None)


class RestApiMethodRoutePlugin(BasePlugin):
    """
    APISpec plugin to generate path from a restapi.method route
    """

    def __init__(self, service):
        super(RestApiMethodRoutePlugin, self).__init__()
        self.converter_mapping = dict(DEFAULT_CONVERTER_MAPPING)
        self._service = service

    # pylint: disable=W8110
    def init_spec(self, spec):
        super(RestApiMethodRoutePlugin, self).init_spec(spec)
        self.spec = spec
        self.openapi_version = spec.openapi_version

    @staticmethod
    def route2openapi(path):
        """Convert an odoo route to an OpenAPI-compliant path.

        :param str path: Odoo route path template.
        """
        return RE_URL.sub(r"{\1}", path)

    # Greatly inspired by flask-apispec
    def route_to_params(self, route):
        """Get parameters from Odoo route"""
        # odoo route are Werkzeug Rule
        rule = Rule(route)
        Map(rules=[rule])

        params = []
        for argument in rule.arguments:
            param = {"in": "path", "name": argument, "required": True}
            type_, format_ = self.converter_mapping.get(
                type(rule._converters[argument]), DEFAULT_TYPE
            )
            schema = {"type": type_}
            if format_ is not None:
                schema["format"] = format_
            param["schema"] = schema
            params.append(param)
        return params

    def path_helper(self, path, operations, parameters, **kwargs):
        params = kwargs.get(ROUTING_DECORATOR_ATTR, {}).get('parameters', {}).get('path')
        params = params.to_openapi_query_parameters(self._service, self.spec) if params else []
        params = {param['name']: param for param in params}
        for param in self.route_to_params(path):
            parameters.append(param)
            if param['name'] in params:
                param.update({
                    'description': params[param['name']]['description'],
                    'schema': params[param['name']]['schema'],
                })

        return self.route2openapi(path)
