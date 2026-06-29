# -*- coding: utf-8 -*-
from odoo.tools.translate import _
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.base_rest.controllers.main import RestController
from odoo.addons.base_rest.components.service import skip_secure_paths, skip_secure_params
from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class FsmApiController(RestController):
    _root_path = "/api/v1/"
    _collection_name = "fsm"
    _default_auth = "public"


class FsmApiService(Component):
    _inherit = "base.rest.service"
    _name = "Field Service Management"
    _usage = "fsm"
    _collection = "fsm"
    _description = ""
    _version = "1.0"
    _components = {}
    _reasons = {}
    _tags = []
    _spec = None

    def __init__(self, work_context):
        super().__init__(work_context)
        try:
            spec = work_context.env['fsm.api.spec'].sudo().search([('collection', '=', False)], limit=1)
            if spec:
                self._spec = spec
                self._name = spec.name
                self._version = spec.version
                self._description = spec.get_description()
                self._reasons = spec.get_reasons()
                self._tags.append({
                    "name": "Saha Hizmetleri",
                    "description": "Saha hizmetleri çağrı yönetimi\n\nSaha hizmetleri Payser API üzerinden çağrı (iş emri) oluşturulmasına, oluşturulan bir iş emrinin durumunun sorgulanmasına ve uygun durumlarda iptal edilebilmesine imkan sağlar.\n\nSaha hizmetleri kapsamında müşteriye ait ürün listesi Payser Hizmet Merkezlerine ve modele göre listelenir.",
                })
                self._components.update({
                    "securitySchemes": {
                        "basicAuth": {
                            "type": "http",
                            "scheme": "basic",
                        },
                    },
                    "security": {
                        "basicAuth": [],
                    },
                    "responses": {
                        "unauthorizedError": {
                            "description": "Eksik veya geçersiz erişim bilgileri",
                            "headers": {
                                "WWW_Authenticate": {
                                    "schema": {
                                        "type": "string"
                                    }
                                }
                            },
                        },
                    },
                })
        except Exception:
            _logger.exception("Failed to initialize FsmApiService")

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/workorders"], "POST")],
        parameters={
            "request": Datamodel("fsm.createworkorder.request"),
        },
        responses={
            "200": Datamodel("fsm.createworkorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Çağrı Yönetimi"],
        summary="İş emri oluştur",
        description="İş emri oluşturmak için kullanılır. İstek gövdesi iş emrinin türüne göre farklılık gösterir.",
    )
    def post_workorder(self, *args, **kwargs):
        return self._spec.execute('createWorkorder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/workorders/<orderId>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getworkorder.path"),
        },
        responses={
            "200": Datamodel("fsm.getworkorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Çağrı Yönetimi"],
        summary="İş emri durum sorgula",
        description="Oluşturulmuş bir iş emrinin detaylarının sorgulanması için kullanılır.\n\nİş emrinin durumu yalnızca Payser tarafından oluşturulmuş orderId ile sorgulanabilir.",
    )
    def get_workorder(self, *args, **kwargs):
        return self._spec.execute('getWorkorder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/workorders/approve/<orderId>"], "POST")],
        parameters={
            "path": Datamodel("fsm.approveworkorder.path"),
            "request": Datamodel("fsm.approveworkorder.request"),
        },
        responses={
            "200": Datamodel("fsm.approveworkorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Çağrı Yönetimi"],
        summary="İş emri durum onayla veya reddet",
        description="Kapanmış bir iş emrinin durumunu onaylamak veya hatalı ilan etmek için kullanılır. Ayrıca BEKLEMEDE durumundaki bir iş emrinde Müşteri tarafındaki blok nedeninin ortadan kaldırıldığını Payser'e iletmek amacıyla da kullanılabilir. Müşteri code alanında ön tanımlı değerler üzerinden blok nedeninin ortadan kaldırıldığını iletir.",
    )
    def post_approve_workorder(self, *args, **kwargs):
        return self._spec.execute('approveWorkorder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/workorders/cancel/<orderId>"], "POST")],
        parameters={
            "path": Datamodel("fsm.cancelworkorder.path"),
        },
        responses={
            "200": Datamodel("fsm.cancelworkorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Çağrı Yönetimi"],
        summary="İş emri iptal et",
        description="Oluşturulmuş bir iş emrinin iptal edilmesi için kullanılır.",
    )
    def post_cancel_workorder(self, *args, **kwargs):
        return self._spec.execute('cancelWorkorder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [],
        webhook=True,
        parameters={
            "request": Datamodel("fsm.webhookworkorder.request"),
        },
        auth="public",
        tags=["Çağrı Yönetimi"],
        summary="İş emri durum bildir",
        description="İş emri durum değişikliğini bildiren webhook.",
    )
    def post_workorder_webhook(self, **kwargs):
        pass

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/inventory/cities/<int:cityId>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinventorycity.path"),
            "request": Datamodel("fsm.getinventorycity.request"),
        },
        responses={
            "200": Datamodel("fsm.getinventorycity.response", code="200", description="Ürün listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Envanter Yönetimi"],
        summary="Ürün envanterini listeleme",
        description="Payser hizmet merkezinde yer alan ürünleri listeler.",
    )
    def get_inventory_cities(self, *args, **kwargs):
        return self._spec.execute('getInventoryCity', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/inventory/cities/<int:cityId>/products/<model>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinventorycityproduct.path"),
            "request": Datamodel("fsm.getinventorycityproduct.request"),
        },
        responses={
            "200": Datamodel("fsm.getinventorycityproduct.response", code="200", description="Ürün listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Envanter Yönetimi"],
        summary="Ürün model envanterini listele",
        description="Payser hizmet merkezinde yer alan ürünleri modele göre listeler.",
    )
    def get_inventory_cities_products(self, *args, **kwargs):
        return self._spec.execute('getInventoryCityProduct', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/inventory/cities/<cityId>/materials/<model>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinventorycitymaterial.path"),
            "request": Datamodel("fsm.getinventorycitymaterial.request"),
        },
        responses={
            "200": Datamodel("fsm.getinventorycitymaterial.response", code="200", description="Malzeme listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Envanter Yönetimi"],
        summary="Malzeme envanterini listele",
        description="Payser hizmet merkezinde yer alan malzemeleri listeler.",
    )
    def get_inventory_cities_materials(self, *args, **kwargs):
        return self._spec.execute('getInventoryCityMaterial', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/saleorders/create"], "POST")],
        parameters={
            "request": Datamodel("fsm.createsaleorder.request"),
        },
        responses={
            "200": Datamodel("fsm.createsaleorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sipariş Yönetimi"],
        summary="Sipariş oluştur ve ürün rezerve et",
        description="Ürün rezerve ederek ön sipariş oluşturulmasını sağlar.\n\nÖn sipariş için teslimatın yapılacağı il ve ilçe bilgisi gönderilmelidir. Bu bilgiye istinaden sevkiyatın yapılacağı depo belirlenir ve ilgili depodan rezervasyon yapılır. Ek olarak satışın yapıldığı kanal ile birlikte rezerve edilecek model ve miktar bilgisi iletilmelidir.\n\nÖn siparişin belirli bir süre içinde onaylanmaması halinde sistem tarafından otomatik iptal yapılır.",
    )
    def post_order_create(self, *args, **kwargs):
        return self._spec.execute('createSaleOrder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/saleorders/approve/<orderId>"], "POST")],
        parameters={
            "path": Datamodel("fsm.approvesaleorder.path"),
            "request": Datamodel("fsm.approvesaleorder.request"),
        },
        responses={
            "200": Datamodel("fsm.approvesaleorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sipariş Yönetimi"],
        summary="Sipariş onayla",
        description="Ürün rezerve ederek ön sipariş oluşturulmasını sağlar. Ön siparişte belirlenmiş teslimat adresinin il ve ilçesinin değiştirilmesine izin verilmez. Farklı bir il ve ilçeye teslimat istenmesi halinde mevcut ön sipariş iptal edilmeli ve yeni bir ön sipariş oluşturulmalıdır.",
    )
    def post_order_approve(self, *args, **kwargs):
        return self._spec.execute('approveSaleOrder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/saleorders/cancel/<orderId>"], "POST")],
        parameters={
            "path": Datamodel("fsm.cancelsaleorder.path"),
        },
        responses={
            "200": Datamodel("fsm.cancelsaleorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sipariş Yönetimi"],
        summary="Sipariş iptal et",
        description="Bir ön siparişin veya onaylanmış ancak dağıtıma çıkmamış bir siparişin (teslimat için belirlenmiş kargo firmasının desteklemesi halinde) iptal edilmesini sağlar.",
    )
    def post_order_cancel(self, *args, **kwargs):
        return self._spec.execute('cancelSaleOrder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/saleorders/query/<orderId>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getsaleorder.path"),
        },
        responses={
            "200": Datamodel("fsm.getsaleorder.response", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sipariş Yönetimi"],
        summary="Siparişin durumunu sorgula",
        description="Bir ön siparişin veya onaylanmış ancak dağıtıma çıkmamış bir siparişin (teslimat için belirlenmiş kargo firmasının desteklemesi halinde) iptal edilmesini sağlar.",
    )
    def get_order_query(self, *args, **kwargs):
        return self._spec.execute('getSaleOrder', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/ordertypes"], "GET")],
        parameters={
            "request": Datamodel("fsm.getinfoordertype.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfoordertype.response", code="200", description="Müşterinin kullanmaya yetkili olduğu iş emri türlerinin listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="İşlem türlerini listele",
        description="Müşterinin kullanabileceği iş emri tiplerini listeler.",
    )
    def get_info_ordertypes(self, *args, **kwargs):
        return self._spec.execute('getInfoOrdertype', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/projects"], "GET")],
        parameters={
            "request": Datamodel("fsm.getinfoproject.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfoproject.response", code="200", description="Müşterinin kullanmaya yetkili olduğu projelerin listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Projeleri listele",
        description="Müşterinin kullanabileceği projeleri listeler.",
    )
    def get_info_projects(self, *args, **kwargs):
        return self._spec.execute('getInfoProject', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/subpartners"], "GET")],
        parameters={
            "request": Datamodel("fsm.getinfosubpartner.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfosubpartner.response", code="200", description="Müşterinin operasyonunda tanımlı alt iş ortaklarının listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Alt carileri listele",
        description="Müşterinin kullanabileceği alt işortaklarını listeler.",
    )
    def get_info_subpartners(self, *args, **kwargs):
        return self._spec.execute('getInfoSubpartner', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/cities"], "GET")],
        parameters={
            "request": Datamodel("fsm.getinfocity.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfocity.response", code="200", description="Payser'in hizmet kapsamında yer alan illerin ve illere ait kodların listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Şehirleri listele",
        description="Payser'in hizmet kapsamında yer alan illeri ve illere ait kodları listeler.",
    )
    def get_info_cities(self, *args, **kwargs):
        return self._spec.execute('getInfoCity', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/cities/<int:cityId>/towns"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinfotown.path"),
            "request": Datamodel("fsm.getinfotown.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfotown.response", code="200", description="Payser'in hizmet kapsamında yer alan ilgili ile ait ilçeleri ve ilçelere ait kodları listeler."),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="İlçeleri listele",
        description="Payser'in hizmet kapsamında yer alan ilgili ile ait ilçeleri ve ilçelere ait kodları listeler.",
    )
    def get_info_cities_towns(self, *args, **kwargs):
        return self._spec.execute('getInfoTown', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/cities/<int:cityId>/towns/<int:townId>/districts"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinfodistrict.path"),
            "request": Datamodel("fsm.getinfodistrict.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfodistrict.response", code="200", description="Payser'in hizmet kapsamında yer alan ilgili il ve ilçeye ait mahalleleri ve mahallelere ait kodların listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Mahalleleri listele",
        description="Payser'in hizmet kapsamında yer alan ilgili il ve ilçeye ait mahalleleri ve mahallelere ait kodları listeler.",
    )
    def get_info_cities_towns_districts(self, *args, **kwargs):
        return self._spec.execute('getInfoDistrict', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/servicezones/cities/<int:cityId>/towns/<int:townId>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinfozone.path"),
            "request": Datamodel("fsm.getinfozone.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfozone.response", code="200", description="Payser'in hizmet verdiği il ve ilçeleri, bu bölgelerde taahhüt edilen hizmet türü ve seviyesi listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Hizmet noktalarını listele",
        description="Payser'in hizmet verdiği il ve ilçeleri, bu bölgelerde taahhüt edilen hizmet türü ve seviyesini listeler.",
    )
    def get_info_zones(self, *args, **kwargs):
        return self._spec.execute('getInfoZone', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/taxoffices/cities/<int:cityId>"], "GET")],
        parameters={
            "path": Datamodel("fsm.getinfotaxoffice.path"),
            "request": Datamodel("fsm.getinfotaxoffice.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfotaxoffice.response", code="200", description="Gelir İdaresi Başkanlığı tarafından ilan edilmiş vergi dairelerinin listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Vergi dairelerini listele",
        description="Gelir İdaresi Başkanlığı tarafından ilan edilmiş vergi dairelerini listeler.",
    )
    def get_info_taxoffices(self, *args, **kwargs):
        return self._spec.execute('getInfoTaxoffice', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/info/statuscodes"], "GET")],
        parameters={
            "request": Datamodel("fsm.getinfostatuscode.request"),
        },
        responses={
            "200": Datamodel("fsm.getinfostatuscode.response", code="200", description="Durum kodları listesi"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Bilgi Servisleri"],
        summary="Durum kodlarını listele",
        description="Servis içinde kullanılan durum kodlarını listeler.",
    )
    def get_info_statuscodes(self, *args, **kwargs):
        return self._spec.execute('getInfoStatuscode', *args, **kwargs)


class FsmDeliveryAPIController(RestController):
    _root_path = "/api/v1/fsm/"
    _collection_name = "delivery"
    _default_auth = "public"


class FsmDeliveryAPIService(Component):
    _inherit = "base.rest.service"
    _name = "Field Service Management: Delivery"
    _usage = "delivery"
    _collection = "delivery"
    _description = ""
    _version = "1.0"
    _components = {}
    _reasons = {}
    _tags = []
    _spec = None

    def __init__(self, work_context):
        super().__init__(work_context)
        try:
            spec = work_context.env['fsm.api.spec'].sudo().search([('collection', '=', 'delivery')], limit=1)
            if spec:
                self._spec = spec
                self._name = spec.name
                self._version = spec.version
                self._description = spec.get_description()
                self._reasons = spec.get_reasons()
                self._tags.append({
                    "name": "Saha Hizmetleri",
                    "description": "Saha hizmetleri çağrı yönetimi\n\nSaha hizmetleri Payser API üzerinden çağrı (iş emri) oluşturulmasına, oluşturulan bir iş emrinin durumunun sorgulanmasına ve uygun durumlarda iptal edilebilmesine imkan sağlar.\n\nSaha hizmetleri kapsamında müşteriye ait ürün listesi Payser Hizmet Merkezlerine ve modele göre listelenir.",
                })
                self._components.update({
                    "securitySchemes": {
                        "basicAuth": {
                            "type": "http",
                            "scheme": "basic",
                        },
                    },
                    "security": {
                        "basicAuth": [],
                    },
                    "responses": {
                        "unauthorizedError": {
                            "description": "Eksik veya geçersiz erişim bilgileri",
                            "headers": {
                                "WWW_Authenticate": {
                                    "schema": {
                                        "type": "string"
                                    }
                                }
                            },
                        },
                    },
                })
        except:
            pass

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/contract/download/<reference>"], "GET")],
        parameters={
            "path": Datamodel("fsm.downloaddeliverycontract.path"),
        },
        responses={
            "200": Datamodel("fsm.response.200", code="200", description="İşlem başarılı", mimetype="application/pdf", filename="Sözleşme.pdf"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sözleşme Servisleri"],
        summary="Sözleşme İndir",
        description="Sözleşmeyi PDF olarak indirir.",
    )
    def download_contract(self, *args, **kwargs):
        return self._spec.execute('downloadDeliveryContract', *args, **kwargs)

    @skip_secure_paths
    @skip_secure_params
    @restapi.method(
        [(["/contract/upload/<reference>"], "POST")],
        parameters={
            "path": Datamodel("fsm.uploaddeliverycontract.path"),
            "request": Datamodel("fsm.uploaddeliverycontract.request", mimetype="application/octet-stream"),
        },
        responses={
            "200": Datamodel("fsm.response.200", code="200", description="İşlem başarılı"),
            "400": Datamodel("fsm.response.400", code="400", description="İşlem başarısız"),
            "401": Datamodel("fsm.response.401", code="401", description="Yetkisiz işlem"),
            "403": Datamodel("fsm.response.403", code="403", description="Yetkisiz hizmet erişim isteği"),
            "404": Datamodel("fsm.response.404", code="404", description="Veri bulunamadı"),
            "422": Datamodel("fsm.response.422", code="422", description="Hatalı istek"),
            "500": Datamodel("fsm.response.500", code="500", description="Beklenmedik hata"),
        },
        auth="public",
        tags=["Sözleşme Servisleri"],
        summary="Sözleşme Yükle",
        description="Sözleşmeyi PDF olarak yükler.",
    )
    def upload_contract(self, *args, **kwargs):
        return self._spec.execute('uploadDeliveryContract', *args, **kwargs)
