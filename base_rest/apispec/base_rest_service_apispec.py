# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import inspect
import textwrap
from apispec import APISpec

from odoo import _

from ..core import _rest_services_databases
from ..tools import ROUTING_DECORATOR_ATTR
from .rest_method_param_plugin import RestMethodParamPlugin
from .rest_method_security_plugin import RestMethodSecurityPlugin
from .restapi_method_route_plugin import RestApiMethodRoutePlugin


class BaseRestServiceAPISpec(APISpec):
    """
    APISpec object from base.rest.service component
    """

    def __init__(self, service_component, **params):
        self._service = service_component
        env = self._service.env
        company = env.company
        website = getattr(company, 'website_id', False)
        if website:
            url = "/web/image/website/%s/logo" % website.id
        else:
            url = "/web/image/res.company/%s/logo" % company.id

        super(BaseRestServiceAPISpec, self).__init__(
            title=self._service._name,
            version=self._service._version,
            openapi_version="3.1.0",
            info={
                "description": textwrap.dedent(getattr(self._service, "_description", "") or ""),
                "x-logo": dict(url=url)
            },
            servers=self._get_servers(),
            plugins=self._get_plugins(),
            tags=self._service._tags,
            components=self._service._components,
        )
        self._params = params

    def _get_servers(self):
        env = self._service.env
        services_registry = _rest_services_databases.get(env.cr.dbname, {})
        collection_path = ""
        for path, spec in list(services_registry.items()):
            if spec["collection_name"] == self._service._collection:
                collection_path = path
                break
        base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")
        return [
            {
                "url": "%s/%s/%s" % (
                    base_url.strip("/"),
                    collection_path.strip("/"),
                    self._service._usage,
                )
            }
        ]

    def _get_plugins(self):
        return [
            RestApiMethodRoutePlugin(self._service),
            RestMethodParamPlugin(self._service),
            RestMethodSecurityPlugin(self._service),
        ]

    def webhook(self, method, values):
        def name(name):
            return ''.join(i and x.capitalize() or x for i, x in enumerate(name.split('_')))

        routing = getattr(method, ROUTING_DECORATOR_ATTR, None)
        operations = {'x-webhook': values}

        for plugin in self.plugins:
            try:
                plugin.operation_helper(operations=operations, **{ROUTING_DECORATOR_ATTR: routing})
            except:
                continue

        self._clean_operations(operations)

        webhook = {
            name(method.__name__): {
                "post": {
                    **values,
                    "responses": {
                        "200": {
                            "description": _("Successful")
                        }
                    }

                }
            }
        }

        if 'webhooks' in self.options:
            self.options['webhooks'].update(webhook)
        else:
            self.options['webhooks'] = webhook

    def _add_method_path(self, method):
        routing = getattr(method, ROUTING_DECORATOR_ATTR)
        values = {}

        summary = routing.get('summary')
        if summary:
            values.update({'summary': summary})

        description = routing.get('description')
        if description:
            values.update({'description': description})

        tags = routing.get('tags')
        if tags:
            values.update({'tags': tags})

        if 'webhook' in routing:
            self.webhook(method, values)
        else:
            for paths, method in routing["routes"]:
                for path in paths:
                    self.path(
                        path,
                        operations={method.lower(): values},
                        **{ROUTING_DECORATOR_ATTR: routing},
                    )

    def generate_paths(self):
        methods = [method for __, method in inspect.getmembers(self._service, inspect.ismethod)]
        methods.sort(key=lambda m: inspect.getsourcelines(m)[1])
        for method in methods:
            routing = getattr(method, ROUTING_DECORATOR_ATTR, None)
            if not routing:
                continue
            self._add_method_path(method)
