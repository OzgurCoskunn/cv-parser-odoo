# -*- coding: utf-8 -*-
import copy
import base64
import logging
import traceback
from lxml import etree
from urllib.parse import urlparse

from odoo import http, _
from odoo.http import request, Response
from odoo.addons.base_rest import restapi
from odoo.tools.mimetypes import guess_mimetype
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.base_rest.tools import ROUTING_DECORATOR_ATTR
from odoo.addons.base_rest.controllers.main import RestController
from odoo.addons.base_rest.components.service import skip_secure_params, skip_secure_response
from odoo.addons.component.core import Component

from ..response import Response400, Response401, Response404

PARAMTYPE = {'integer': 'int'}

_logger = logging.getLogger(__name__)

NAMESPACES = {
    'wsdl': {
        's': 'http://www.w3.org/2001/XMLSchema',
        'xop': 'http://www.w3.org/2004/08/xop/include',
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
        'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
        'soapenc': 'http://schemas.xmlsoap.org/soap/encoding/',
        'http': 'http://schemas.xmlsoap.org/wsdl/http/',
        'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'tns': 'https://%s/api/soap/%s/',
    },
    'soap': {
        'http': 'http://schemas.xmlsoap.org/soap/http',
        'envelope': 'http://schemas.xmlsoap.org/soap/envelope/'
    }
}


class FsmSoap(Component):
    _inherit = "base.rest.service"
    _name = "fsm.soap"

    def _soap_get_usage_path(self):
        return 'fsm' if self._usage == 'fsm' else 'fsm/%s' % self._usage

    @staticmethod
    def _soap_add_types_elements(element, fields, ns, sch):
        ctype = etree.SubElement(element, '{%s}complexType' % ns['s'])
        sequence = etree.SubElement(ctype, '{%s}sequence' % ns['s'])
        required = fields.get('required', [])
        for key, field in fields['properties'].items():
            if field['type'] == 'object':
                elem = etree.SubElement(sequence, '{%s}element' % ns['s'], {
                    'minOccurs': '1' if key in required else '0',
                    'maxOccurs': '1',
                    'name': key,
                })
                FsmSoap._soap_add_types_elements(elem, field, ns, sch)
            elif field['type'] == 'array':
                elem = etree.SubElement(sequence, '{%s}element' % ns['s'], {
                    #'type': 'tns:%s' % key,
                    'maxOccurs': 'unbounded',
                    'name': key,
                })
                FsmSoap._soap_add_types_elements(elem, field['items'], ns, sch)
            else:
                etree.SubElement(sequence, '{%s}element' % ns['s'], {
                    'type': 's:%s' % PARAMTYPE.get(field['type'], field['type']),
                    'minOccurs': '1' if key in required else '0',
                    'maxOccurs': '1',
                    'name': key,
                })

    @staticmethod
    def _soap_add_types(root, methods, ns):
        tree = etree.SubElement(root, '{%s}types' % ns['wsdl'])
        schema = etree.SubElement(tree, '{%s}schema' % ns['s'], {
            'elementFormDefault': 'qualified',
            'targetNamespace': ns['tns']
        })

        for name, io in methods.items():
            element = etree.SubElement(schema, '{%s}element' % ns['s'], {'name': '%sRequest' % name})
            FsmSoap._soap_add_types_elements(element, io['input'], ns, schema)

            element = etree.SubElement(schema, '{%s}element' % ns['s'], {'name': '%sResponse' % name})
            FsmSoap._soap_add_types_elements(element, io['output'], ns, schema)

    @staticmethod
    def _soap_add_messages(root, methods, ns):
        for name in methods.keys():
            tree = etree.SubElement(root, '{%s}message' % ns['wsdl'], {'name': '%sInput' % name})
            etree.SubElement(tree, '{%s}part' % ns['wsdl'], {
                'name': 'parameters',
                'element': 'tns:%sRequest' % name,
            })

            tree = etree.SubElement(root, '{%s}message' % ns['wsdl'], {'name': '%sOutput' % name})
            etree.SubElement(tree, '{%s}part' % ns['wsdl'], {
                'name': 'parameters',
                'element': 'tns:%sResponse' % name,
            })

    @staticmethod
    def _soap_add_ports(root, methods, ns):
        tree = etree.SubElement(root, '{%s}portType' % ns['wsdl'], {'name': 'ServicePort'})
        for name in methods.keys():
            operation = etree.SubElement(tree, '{%s}operation' % ns['wsdl'], {'name': name})
            etree.SubElement(operation, '{%s}documentation' % ns['wsdl'], nsmap={'wsdl': ns['wsdl']}).text = name
            etree.SubElement(operation, '{%s}input' % ns['wsdl'], {'message': 'tns:%sInput' % name})
            etree.SubElement(operation, '{%s}output' % ns['wsdl'], {'message': 'tns:%sOutput' % name})

    @staticmethod
    def _soap_add_bindings(root, methods, ns):
        tree = etree.SubElement(root, '{%s}binding' % ns['wsdl'], {'name': 'ServiceSoap', 'type': 'tns:ServicePort'})
        etree.SubElement(tree, '{%s}binding' % ns['soap'], {'transport': NAMESPACES['soap']['http']})
        for name in methods.keys():
            operation = etree.SubElement(tree, '{%s}operation' % ns['wsdl'], {'name': name})
            etree.SubElement(operation, '{%s}operation' % ns['soap'], {
                'soapAction': '%s%s' % (ns['tns'], name),
                'style': 'document'
            })
            for method in ['input', 'output']:
                element = etree.SubElement(operation, '{%s}%s' % (ns['wsdl'], method))
                #if any(m['type'] == 'base64Binary' for m in methods[name][method]):
                #    multipart = etree.SubElement(element, '{%s}multipartRelated' % ns['mime'])
                #    part = etree.SubElement(multipart, '{%s}part' % ns['mime'], {'name': 'Body'})
                #    etree.SubElement(part, '{%s}body' % ns['soap'], {'use': 'literal'})
                #    part = etree.SubElement(multipart, '{%s}part' % ns['mime'], {'name': 'Document'})
                #    etree.SubElement(part, '{%s}content' % ns['mime'], {'part': 'File', 'type': 'application/pdf'})
                #else:
                #    etree.SubElement(element, '{%s}body' % ns['soap'], {'use': 'literal'})
                etree.SubElement(element, '{%s}body' % ns['soap'], {'use': 'literal'})

        tree = copy.deepcopy(tree)
        tree.set('name', 'ServiceSoap12')
        root.append(tree)

    @staticmethod
    def _soap_add_services(root, ns):
        tree = etree.SubElement(root, '{%s}service' % ns['wsdl'], {'name': 'Service'})
        port = etree.SubElement(tree, '{%s}port' % ns['wsdl'], {'name': 'ServiceSoap', 'binding': 'tns:ServiceSoap'})
        etree.SubElement(port, '{%s}address' % ns['soap'], {'location': ns['tns']})
        port = etree.SubElement(tree, '{%s}port' % ns['wsdl'], {'name': 'ServiceSoap12', 'binding': 'tns:ServiceSoap12'})
        etree.SubElement(port, '{%s}address' % ns['soap12'], {'location': ns['tns']})

    @staticmethod
    def _soap_get_params(item):
        def parse(v, n):
            if list(n):
                v[etree.QName(n.tag).localname] = deserialize(n)
            else:
                v[etree.QName(n.tag).localname] = n.text and n.text.strip() or ''

        def deserialize(node):
            if etree.QName(node.tag).localname == 'approveWoInfoList':
                values = []
            else:
                values = {}
            for n in node:
                if n.tag is etree.Comment:
                    continue
                if isinstance(values, list):
                    v = {}
                    parse(v, n)
                    values.append(v)
                else:
                    parse(values, n)
            return values

        return deserialize(item)

    @staticmethod
    def _soap_get_response(method, address, values={}, attachments={}):
        def serialize(node, key, val):
            n = etree.SubElement(node, '{%s}%s' % (ns0['ns0'], key))
            if isinstance(val, list):
                for va in val:
                    if isinstance(va, dict):
                        for k, v in va.items():
                            serialize(n, k, v)
                    else:
                        n.text = '%s' % (va,)
            elif isinstance(val, dict):
                for k, v in val.items():
                    serialize(n, k, v)
            else:
                n.text = '%s' % (val,)

        nss = {
            'soap': NAMESPACES['soap']['envelope'],
            'xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsd': "http://www.w3.org/2001/XMLSchema"
        }
        ns0 = {None: address}
        root = etree.Element('{%s}Envelope' % nss['soap'], nsmap=nss)
        body = etree.SubElement(root, '{%s}Body' % nss['soap'])
        tree = etree.SubElement(body, '%sResponse' % (method,), nsmap=ns0)

        for key, val in values.items():
            if key in attachments:
                etree.SubElement(tree, '{%s}%s' % (ns0['ns0'], key), href='cid:%s' % attachments[key])
            else:
                serialize(tree, key, val)
        result = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
        if attachments:
            result = f"""--boundary
Content-Type: text/xml; charset=UTF-8
Content-Transfer-Encoding: 8bit
Content-ID: <Body>

{result.decode('utf-8')}
"""
            for key, val in attachments.items():
                result += f"""
--boundary
Content-Type: application/pdf; name={val}
Content-Transfer-Encoding: base64
Content-ID: <{val}>
Content-Disposition: attachment; name="{val}"; filename="{val}"

{values[key].decode('utf-8')}

"""
            result += f"""
--boundary--
"""
        return result

    @staticmethod
    def _soap_pretty_xml(data):
        root = etree.fromstring(data)
        return etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)


class FsmSoapController(RestController):
    _root_path = "/api/soap/"
    _collection_name = "soap"
    _default_auth = "public"


class FsmSoapService(Component):
    _inherit = "fsm.soap"
    _name = "Field Service Management: SOAP"
    _usage = "fsm"
    _collection = "soap"
    _description = ""
    _version = "1.2"
    _components = {}
    _reasons = {}
    _tags = []
    _spec = None

    @skip_secure_params
    @skip_secure_response
    @restapi.method(
        [(["/WSDL"], "GET")],
        parameters={
            "createWorkorder": Datamodel("fsm.post.workorder.request", mimetype="text/xml"),
            "queryWorkorder": Datamodel("fsm.get.workorder.path", mimetype="text/xml"),
            "approveWorkorder": Datamodel("fsm.post.workorder.approve.path", mimetype="text/xml"),
            "cancelWorkorder": Datamodel("fsm.post.workorder.cancel.path", mimetype="text/xml"),
        },
        responses={},
        auth="public",
        tags=["SOAP"],
        summary="WSDL",
        description="Get WSDL document",
    )
    def wsdl(self):
        try:
            token = self._auth(self.env)
            methods = {}
            routing = getattr(self.wsdl, ROUTING_DECORATOR_ATTR, None)
            parameters = routing.get('parameters', {}).items()
            for key, model in parameters:
                methods[key] = {
                    'input': model.to_json_schema(self, None, 'input'),
                    'output': model.to_json_schema(self, None, 'output'),
                }

            url = urlparse(request.httprequest.url)
            ns = {**NAMESPACES['wsdl']}
            ns['tns'] = ns['tns'] % (url.netloc, self._soap_get_usage_path())

            root = etree.Element('{%s}definitions' % ns['wsdl'], {'targetNamespace': ns['tns']}, nsmap=ns)
            self._soap_add_types(root, methods, ns)
            self._soap_add_messages(root, methods, ns)
            self._soap_add_ports(root, methods, ns)
            self._soap_add_bindings(root, methods, ns)
            self._soap_add_services(root, ns)

            data = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
            headers = [('Content-Type', 'text/xml; charset=utf-8'), ('Cache-Control', 'max-age=%s' % http.STATIC_CACHE)]
            return request.make_response(data, headers)
        except Response400 as e:
            return Response(str(e), status=400)
        except Response401:
            return Response('Access Denied', status=401)
        except Response404:
            return Response('Not Found', status=404)
        except Exception as e:
            _logger.error(traceback.format_exc())
            _logger.error(e)
            return Response('Internal Server Error', status=500)


class FsmSoapDeliveryController(RestController):
    _root_path = "/api/soap/fsm/"
    _collection_name = "soap1"
    _default_auth = "public"


class FsmSoapDeliveryService(Component):
    _inherit = "fsm.soap"
    _name = "Field Service Management: Delivery SOAP"
    _usage = "delivery"
    _collection = "soap1"
    _description = ""
    _version = "1.2"
    _components = {}
    _reasons = {}
    _tags = []
    _spec = None

    @skip_secure_params
    @skip_secure_response
    @restapi.method(
        [(["/WSDL"], "GET")],
        parameters={},
        responses={},
        auth="public",
        tags=["SOAP"],
        summary="WSDL",
        description="Get WSDL document",
    )
    def wsdl(self):
        try:
            token = self._auth()
            url = urlparse(request.httprequest.url)
            ns = {**NAMESPACES['wsdl']}
            ns['tns'] = ns['tns'] % (url.netloc, self._usage)

            root = etree.Element('{%s}definitions' % ns['wsdl'], {'targetNamespace': ns['tns']}, nsmap=ns)
            self._soap_add_types(root, ns)
            self._soap_add_messages(root, ns)
            self._soap_add_ports(root, ns)
            self._soap_add_bindings(root, ns)
            self._soap_add_services(root, ns)

            data = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
            headers = [('Content-Type', 'text/xml; charset=utf-8'), ('Cache-Control', 'max-age=%s' % http.STATIC_CACHE)]
            return request.make_response(data, headers)
        except Response400 as e:
            return Response(str(e), status=400)
        except Response401:
            return Response('Access Denied', status=401)
        except Response404:
            return Response('Not Found', status=404)
        except Exception as e:
            _logger.error(e)
            return Response('Internal Server Error', status=500)

    @skip_secure_params
    @skip_secure_response
    @restapi.method(
        [(["/"], "POST")],
        parameters={},
        responses={},
        auth="public",
        tags=["SOAP"],
        summary="SOAP",
        description="Post SOAP Data",
    )
    def soap(self):
        try:
            token = self._auth()
            data = request.httprequest.get_data()
            url = urlparse(request.httprequest.url)
            address = NAMESPACES['wsdl']['tns'] % (url.netloc, self._usage)
            root = etree.fromstring(data)
            item = root.xpath('//ns:*', namespaces={'ns': address})[0]
            method = etree.QName(item.tag).localname
            params = self._soap_get_params(method, item)
            reference = params.get('Reference')
            if not reference:
                raise Response400('Reference has not been specified.')

            picking = self.env['stock.picking'].sudo().search([('carrier_tracking_ref', '=', reference)], limit=1)
            if not picking:
                raise Response404(None)

            if method == 'Download':
                contract = getattr(picking, 'delivery_contract_rendered_id', None)
                if not contract:
                    pdf = picking.carrier_id.render_contract()
                    contract = self.env['ir.attachment'].sudo().create({
                        'type': 'binary',
                        'name': _('%s (rendered).pdf') % reference,
                        'mimetype': 'application/pdf',
                        'delivery_contract_rendered': True,
                        'res_model': picking._name,
                        'res_id': picking.id,
                        'datas': base64.b64encode(pdf),
                    })

                result = self._soap_get_response(method, address, values={'Document': contract.datas or b''}, attachments={'Document': '%s.pdf' % reference})
                headers = [
                    ("MIME-Version", "1.0"), ('Cache-Control', 'no-store'),
                    ('Content-Type', 'multipart/related; type="text/xml"; charset=utf-8; start="<Body>"'),
                ]
                return Response(result, status=200, headers=headers)

            elif method == 'Upload':
                document = params.get('Document')
                if not document:
                    raise Response400('Document has not been specified.')

                contract = getattr(picking, 'delivery_contract_signed_id', None)
                contract_signed = not contract
                mimetype = guess_mimetype(document)
                extension = '.' + mimetype.split('/')[1]
                if extension == '.svg+xml':
                    extension = '.svg'
                attachment = self.env['ir.attachment'].sudo().create({
                    'type': 'binary',
                    'name': '%s%s%s' % (reference, _(' (signed)') if contract_signed else '', extension),
                    'delivery_contract_signed': contract_signed,
                    'res_model': picking._name,
                    'res_id': picking.id,
                    'mimetype': mimetype,
                    'datas': document,
                })

                headers = [('Cache-Control', 'no-store')]
                return Response(None, status=200, headers=headers)

        except Response400 as e:
            return Response(str(e), status=400)
        except Response401:
            return Response('Access Denied', status=401)
        except Response404:
            return Response('Not Found', status=404)
        except Exception as e:
            _logger.error(e)
            return Response('Internal Server Error', status=500)
