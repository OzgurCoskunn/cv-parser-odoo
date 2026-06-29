# Copyright 2020 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import marshmallow
from apispec.ext.marshmallow.openapi import OpenAPIConverter
from marshmallow.exceptions import ValidationError

from odoo import _
from odoo.http import Response, content_disposition
from odoo.exceptions import UserError
from odoo.addons.base_rest import restapi


class Datamodel(restapi.RestMethodParam):
    def __init__(self, name, is_list=False, partial=None, **kwargs):
        """

        :param name: The datamodel name
        :param is_list: Should be set to True if params is a collection so that
                        the object will be de/serialized from/to a list
        :param partial: Whether to ignore missing fields and not require
            any fields declared. Propagates down to ``Nested`` fields as well. If
            its value is an iterable, only missing fields listed in that iterable
            will be ignored. Use dot delimiters to specify nested fields.
        """
        self._name = name
        self._is_list = is_list
        self._partial = partial
        self._code = kwargs.get('code')
        self._desc = kwargs.get('description')
        self._mimetype = kwargs.get('mimetype')
        self._filename = kwargs.get('filename')

    def from_params(self, service, params, raise_exception=True):
        ModelClass = service.env.datamodels[self._name]
        try:
            return ModelClass.load(
                params,
                many=self._is_list,
                partial=self._partial,
            )
        except ValidationError as ve:
            if raise_exception:
                raise UserError(_("BadRequest %s") % ve.messages) from ve
            return ve

    def to_response(self, service, result):
        headers = None
        mimetype = None
        status = int(self._code or "200")
        if isinstance(result, bytes):
            mimetype = self._mimetype or "application/json"
            filename = self._filename or _("File")
            if mimetype.endswith('/pdf') and not filename.endswith('.pdf'):
                filename += '.pdf'
            headers= {
                'Content-Type': mimetype,
                'Content-Length': len(result),
                'Content-Disposition': content_disposition(filename),
            }
        elif isinstance(result, dict):
            mimetype = "application/json"
            ModelClass = service.env.datamodels[self._name]
            ModelData = ModelClass(**result)
            if self._is_list:
                result = [i.dump() for i in ModelData]
            else:
                result = ModelData.dump()
            errors = ModelClass.validate(result, many=self._is_list)
            if errors:
                raise SystemError(_("Invalid Response %s") % errors)
            result = json.dumps(result)

        return Response(result, status=status, mimetype=mimetype, headers=headers)

    def to_openapi_query_parameters(self, service, spec):
        converter = self._get_converter()
        schema = self._get_schema(service)
        return converter.schema2parameters(schema, location="query")

    # TODO, we should probably get the spec as parameters. That should
    # allows to add the definition of a schema only once into the specs
    # and use a reference to the schema into the parameters
    def to_openapi_requestbody(self, service, spec):
        request = {}

        mimetype = self._mimetype or "application/json"
        if mimetype == "application/octet-stream":
            schema = {"type": "string", "format": "base64"}
        else:
            schema = self.to_json_schema(service, spec, "input")
            if not schema.get('properties'):
                schema = None
        if schema:
            request['content'] = {
                mimetype: {"schema": schema}
            }

        return request

    def to_openapi_responses(self, service, spec, code="", desc=""):
        code = code or "200"
        response = {
            code: {"description": desc}
        }

        mimetype = self._mimetype or "application/json"
        if mimetype == "application/pdf":
            schema = {"type": "string", "format": "binary"}
        else:
            schema = self.to_json_schema(service, spec, "output")
            if not schema.get('properties'):
                schema = None
        if schema:
            response[code]['content'] = {
                mimetype: {"schema": schema}
            }

        return response

    def to_json_schema(self, service, spec, direction):
        converter = self._get_converter()
        schema = self._get_schema(service)
        return converter.resolve_nested_schema(schema)

    def _get_schema(self, service):
        return service.env.datamodels[self._name].get_schema(many=self._is_list)

    def _get_converter(self):
        return OpenAPIConverter("3.1", self._schema_name_resolver, None)

    def _schema_name_resolver(self, schema):
        # name resolver used by the OpenapiConverter. always return None
        # to force nested schema definition
        return None


restapi.Datamodel = Datamodel
