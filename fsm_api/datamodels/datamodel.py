# -*- coding: utf-8 -*-
from marshmallow import fields, validate
from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class Request0(Datamodel):
    _name = "fsm.request.0"


class Response200(Datamodel):
    _name = "fsm.response.200"


class Response400Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.400.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": "C1400"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": "Hatalı bir istekte bulundunuz"})


class Response400(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.400"

    errors = fields.List(NestedModel("fsm.response.400.error"), required=False, allow_none=False, metadata={})


class Response401Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.401.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": "C1401"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": "Kullanıcı bilgileri hatalı"})


class Response401(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.401"

    errors = fields.List(NestedModel("fsm.response.401.error"), required=False, allow_none=False, metadata={})


class Response403Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.403.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": "C1403"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": "Bu hizmete erişim yetkiniz yoktur"})


class Response403(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.403"

    errors = fields.List(NestedModel("fsm.response.403.error"), required=False, allow_none=False, metadata={})


class Response404Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.404.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": "C1404"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": "Veri bulunamadı."})


class Response404(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.404"

    errors = fields.List(NestedModel("fsm.response.404.error"), required=False, allow_none=False, metadata={})


class Response422ErrorDetail(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.422.error.detail"

    field = fields.String(required=False, allow_none=False, metadata={"description": "Hatalı alan adı", "example": "alanAdi"})
    issue = fields.String(required=False, allow_none=False, metadata={"description": "Hatanın açıklaması", "example": "Bu alan boş olamaz."})


class Response422Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.422.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": ""})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": ""})
    details = fields.List(NestedModel("fsm.response.422.error.detail"), required=False, allow_none=False, metadata={})


class Response422(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.422"

    errors = fields.List(NestedModel("fsm.response.422.error"), required=False, allow_none=False, metadata={})

class Response500Error(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.500.error"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Hata kodu", "example": "C1500"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Hata mesajı", "example": "Beklenmedik bir hata oluştu"})


class Response500(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.response.500"

    errors = fields.List(NestedModel("fsm.response.500.error"), required=False, allow_none=False, metadata={})


class PaginationRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.pagination.request"

    offset = fields.Integer(required=False, allow_none=False, dump_default=0, metadata={"description": "Veri gösterilmeye başlanacak sıra numarasıdır"})
    limit = fields.Integer(required=False, allow_none=False, dump_default=10, metadata={"description": "Bir listede gösterilecek en yüksek veri sayısıdır"})


class PaginationDetail(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.pagination.detail"

    offset = fields.Integer(required=False, allow_none=False, metadata={"description": "Veri gösterilmeye başlanacak sıra numarasıdır"})
    pageCount = fields.Integer(required=False, allow_none=False, metadata={"description": "Sayfada yer alan veri adedi"})
    pageSize = fields.Integer(required=False, allow_none=False, metadata={"description": "Bir sayfada yer alan veri adedi"})


class PaginationResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.pagination.response"

    totalCount = fields.Integer(required=False, allow_none=False, metadata={"description": "Toplam veri adedi"})
    pagination = NestedModel("fsm.pagination.detail", required=False, allow_none=False, metadata={})


class WorkorderCountry(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.country"

    id = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ülkenin ISO kodu", "example": "TR"})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ülkenin adı", "example": "Türkiye"})


class WorkorderCity(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.city"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ilin id bilgisi", "example": 34})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ilin adı", "example": "İstanbul"})


class WorkorderTown(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.town"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ilçenin id bilgisi", "example": 1604})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu ilçenin adı", "example": "Sarıyer"})


class WorkorderDistrict(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.district"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu mahallenin id bilgisi", "example": 34141})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu mahallenin adı", "example": "Maslak"})


class WorkorderProject(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.project"

    id = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Çağrının ait olduğu projenin tekil ID bilgisi", "example": "c4249f1c-efe9-4340-a1b5-d0f27817b3a0"})
    #name = fields.String(required=False, allow_none=False, metadata={"description": "Çağrının ait olduğu projenin isim bilgisi", "example": "Sadakat Kart Projesi"})


class WorkorderAddressPrimary(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.address.primary"

    contactName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri yetkilisinin adı", "example": "İsim Soyisim"})
    phoneNumber1 = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin birincil telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    phoneNumber2 = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin ikincil telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    tradeRegistrationNumber = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin ticaret sicil numarası", "example": "123456-0"})
    city = NestedModel("fsm.workorder.city", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    town = NestedModel("fsm.workorder.town", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    district = NestedModel("fsm.workorder.district", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    address = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin UAVT kodu", "example": "34073041"})


class WorkorderAddressService(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.address.service"

    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri yetkilisinin adı", "example": "ABC Ticaret Ltd. Şti. İzmir Şubesi"})
    tableName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin hizmet yerinin tabela adı", "example": "Akasya Çiçek"})
    contactName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri yetkilisinin adı", "example": "İsim Soyisim"})
    phoneNumber1 = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin birincil telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    phoneNumber2 = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin ikincil telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    city = NestedModel("fsm.workorder.city", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    town = NestedModel("fsm.workorder.town", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    district = NestedModel("fsm.workorder.district", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    address = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin UAVT kodu", "example": "34073041"})


class WorkorderAppointment(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.appointment"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Randevuya ait id bilgisi. Payser tarafından her bir randevu için üretilen tekil değerdir.", "example": ""})
    createDate = fields.DateTime(required=False, allow_none=False, metadata={"description": "Randevu oluşturulma tarihi", "example": ""})
    appointmentDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "Randevu tarihi", "example": ""})
    contactName = fields.String(required=False, allow_none=True, metadata={"description": "İletişim kurulan üye işyeri yetkilisi", "example": ""})
    code = fields.String(required=False, allow_none=False, metadata={"description": "Randevu sebebi kodu", "example": ""})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Randevu sebebi mesajı", "example": ""})
    detail = fields.String(required=False, allow_none=False, metadata={"description": "Randevuya ait detay bilgileri. Payser tarafından ihtiyaç halinde girilecek açıklama alanı.", "example": ""})
    documents = fields.List(fields.Url, required=False, allow_none=False, metadata={"description": "Randevuya ait dokümana/görsele erişim yolu"})


class WorkorderAccesory(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.accesory"

    name = fields.String(required=False, allow_none=False, metadata={"description": "Aksesuarın adı (adaptör, pil, ön kapak, arka kapak, vb.)", "example": ""})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Aksesuarın seri numarası bilgisi", "example": ""})
    operationType = fields.String(required=False, allow_none=False, metadata={"description": "Aksesuar için yapılan işlem bilgisi", "example": "TESLIM_EDILDI"})
    accesoryStatus = fields.String(required=False, allow_none=False, metadata={"description": "Aksesuarın durum bilgisi", "example": "SAGLAM"})
    image = fields.Url(required=False, allow_none=False, metadata={"description": "Aksesuarın görseline erişim yolu", "example": ""})


class WorkorderApplication(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.application"

    name = fields.String(required=False, allow_none=False, metadata={"description": "Uygulama adı", "example": "BKM"})
    description = fields.String(required=False, allow_none=False, metadata={"description": "Uygulama açıklaması", "example": "BKM234SRM"})
    version = fields.String(required=False, allow_none=False, metadata={"description": "Uygulama sürümü", "example": "v1.4.5"})


class WorkorderSetup(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.setup"

    setupId = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kurulum ID bilgisi (Örnek:PAX ID)", "example": "PAX112233445"})
    setupKey = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kurulum anahtarı", "example": "BMK234SRM"})
    merchantId = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyeri numarası", "example": "MER1234"})
    applications = fields.List(NestedModel("fsm.workorder.application"), required=False, allow_none=False, metadata={})


class WorkorderTransaction(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.transaction"

    transactionDate = fields.String(required=False, allow_none=True, metadata={"description": "İşlem tarihi", "example": "2024-03-19T18:45:01Z"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten kod", "example": "COLLECTED"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten mesaj", "example": ""})
    statusDetail = fields.String(required=False, allow_none=False, metadata={"description": "İşlem açıklaması", "example": "Teslim edildi - Merve A***** (Kendisi)"})
    nonDeliveryReason = fields.String(required=False, allow_none=True, metadata={"description": "Teslim edilmeme sebebi", "example": "REFUSED"})
    nonDeliveryReasonMessage = fields.String(required=False, allow_none=True, metadata={"description": "İşlem edilmeme sebebi açıklaması", "example": "Alıcı Kabul Etmiyor"})


class WorkorderList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.list"

    orderId = fields.String(required=False, allow_none=False, metadata={"description": "Payser tarafından oluşturulmuş iş emrine özel tekil id bilgisi"})
    orderType = fields.String(required=False, allow_none=False, metadata={"description": "İş emrinin tip bilgisi"})


class WorkorderMaterial(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.material"

    name = fields.String(required=False, allow_none=False, metadata={"description": "Malzemenin Payser depolarında kayıtlı adı", "example": "Rulo Logolu"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Malzemeye Payser tarafından verilmiş seri numarası", "example": "PYS412401924"})
    count = fields.Integer(required=False, allow_none=False, metadata={"description": "Malzeme adedi", "example": 500})


class WorkorderDocumentInformationDetail(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.document.information.detail"

    key = fields.String(required=False, allow_none=False, metadata={"description": "Belgede yer alacak diğer bilginin adı"})
    value = fields.String(required=False, allow_none=False, metadata={"description": "Belgede yer alacak diğer bilginin değeri"})


class WorkorderDocumentInformation(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.document.information"

    identityNumber = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri yetkilisinin TCKN'si"})
    identityName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri yetkilisinin adı"})
    birthday = fields.Date(required=False, allow_none=False, metadata={"description": "Üye işyeri yetkilisinin doğum tarihi"})
    placeOfBirth = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyeri yetkilisinin doğum yeri"})
    iban = fields.String(required=False, allow_none=False, metadata={"description": "Belge üzerindeki IBAN numarası"})
    details = fields.List(NestedModel("fsm.workorder.document.information.detail"), required=False, allow_none=False, metadata={})


class WorkorderDocument(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.workorder.document"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Belgenin id bilgisi. Her bir belgeye özel Payser tarafından tanımlanmış tekil bilgidir. Payser tarafından üretilen bu id bilgisi belgenin uygun yerine eklenir."})
    type = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Belge türü. Her bir yeni belge türüne/sürümüne özel Payser tarafından üretilip müşteriyle bu bilgi paylaşılır."})
    name = fields.String(required=False, allow_none=False, metadata={"description": "Belgenin adı.", "example": "Üye işyeri sözleşmesi"})
    information = NestedModel("fsm.workorder.document.information", required=False, allow_none=False, metadata={})


class PostWorkorderMerchant(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createworkorder.merchant"

    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri unvanı", "example": "ABC Ticaret Ltd. Şti."})
    tableName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyerinin tabela adı", "example": "Flora Çiçekçilik"})
    taxNumber = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Üye işyeri VKN veya TCKN", "example": "5205906683"})
    taxOffice = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyeri vergi dairesi", "example": "MASLAK V.D."})
    primaryAddress = NestedModel("fsm.workorder.address.primary", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    serviceAddress = NestedModel("fsm.workorder.address.service", required=False, allow_none=False, metadata={})


class PostWorkorderProduct(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createworkorder.product"

    productType = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün türü (POS, SIM, vb.)", "example": "POS"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürüne ait seri numarası bilgisi. KURULUM iş emirlerinde seri numarası iletilmez. DEGISIM iş emirlerinde geri alınacak cihazı belirlemek için iletilmelidir.", "example": ""})
    serialReference = fields.String(required=False, allow_none=False, metadata={"description": "Ürüne ait seri numarası referans bilgisi. KURULUM iş emirlerinde seri numarası iletilmez. DEGISIM iş emirlerinde geri alınacak cihazı belirlemek için iletilmelidir.", "example": ""})
    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün model bilgisi. Ürünün model bilgisi iletilmeden önce Envanter servisinden ilgili modelin o ilde yer alan kullanılabilir miktarı dikkate alınmalıdır.", "example": ""})
    operatingSystem = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün işletim sistemini belirtir. model alanından belirtilen model bilgisine sahip ürünün ilgili ilde stoğunun olmaması halinde uyumlu cihazın KURULUM'U isteniyorsa bu alan dolu gönderilmelidir. Boş gönderilmesi halinde yalnızca ilgili modelle KURULUM yapılacaktır. Ürünün model ve işletim sistemi bilgisi boş iletilirse herhangi bir model cihaza KURULUM yapılır.", "example": "ANDROID"})
    orderType = fields.String(required=False, allow_none=False, metadata={"description": "İş emri kapsamında ürünle ilgili yapılacak işlemin bilgisidir. DEGISIM iş emirlerinde geri alınacak cihaz GERI_ALIM, verilecek cihaz KURULUM olarak iletilmelidir.", "example": "KURULUM"})
    operationType = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kullanılacağı operasyon türünü belirtir.", "example": "EFTPOS"})
    subpartner = fields.String(required=False, allow_none=False, metadata={"description": "Operasyonun hangi alt iş ortağı için yapılacağı bilgisi. Örneğin sadece belirli bir alt iş ortağına ait cihazlarla iş emrine hizmet verilmesi isteniyorsa kullanılır. Müşteri adına tanımlı alt iş ortaklarına /info/subpartners servisinden ulaşılabilir.", "example": "IS_ORTAGI_A"})
    operator = fields.String(required=False, allow_none=False, metadata={"description": "Kullanılacak SIM kartın operatör bilgisi", "example": ""})


class PostWorkorderRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createworkorder.request"

    customerOrderId = fields.String(required=False, allow_none=False, metadata={"description": "İş emri için müşteri tarafından oluşturulmuş ID bilgisi. Müşteri tarafından oluşturulmuş Id değeri GUID olarak atanmalıdır.", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})
    orderType = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "İş emrinin tip bilgisi. Müşteri, kullanabileceği iş emri tiplerine /info/ordertypes servisinden ulaşabilir.", "example": "ARIZA"})
    orderDescription = fields.String(required=False, allow_none=False, metadata={"description": "İş emrinin açıklama bilgisi", "example": "Üye işyeri cihazının şarj olmadığını belirtmektedir."})
    sla = fields.String(required=False, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Talebin SLA koşullarını belirtir. SLA koşulları Payser tarafından tanımlanır ve müşteriyle paylaşılır.", "example": "STANDART"})
    channel = fields.String(required=False, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Kanal bilgisi.", "example": ""})
    project = NestedModel("fsm.workorder.project", required=False, allow_none=False, metadata={"description": "Müşteri tarafından projeli takip talep edilmesi halinde kullanılır. Açılacak tüm iş emirlerinde aynı id ve isim bilgisinin iletilmesi halinde bu iş emirleri Payser tarafından ayrı bir şekilde gruplanır ve raporlanır. İlgili iş emirleri açılmadan önce proje Id bilgisi Payser tarafından üretilip Müşteri ile paylaşılır. SLA koşulları Payser ve Müşteri arasındaki mutabakat ile belirlenir ve işletilir. Payser tarafından oluşturulmamış bir proje ile iş emri açılmasına izin verilmez. Müşteri kullanabileceği projelere info/projects servisinden ulaşabilir."})
    merchant = NestedModel("fsm.createworkorder.merchant", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    products = fields.List(NestedModel("fsm.createworkorder.product"), required=False, allow_none=False, metadata={})
    setup = NestedModel("fsm.workorder.setup", required=False, allow_none=False, metadata={})
    material = NestedModel("fsm.workorder.material", required=False, allow_none=False, metadata={})
    document = NestedModel("fsm.workorder.document", required=False, allow_none=False, metadata={})


class PostWorkorderResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createworkorder.response"

    customerOrderId = fields.String(required=False, allow_none=False, metadata={"description": "İş emri için müşteri tarafından oluşturulmuş ID bilgisi"})
    parentOrderId = fields.String(required=False, allow_none=False, metadata={"description": "Birden fazla iş emri oluşması halinde kök ID bilgisi"})
    workOrders = fields.List(NestedModel("fsm.workorder.list"), required=False, allow_none=False, metadata={})


class GetWorkorderPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Payser tarafından oluşturulmuş iş emrine özel tekil ID bilgisi", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})


class GetWorkorderProduct(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.product"

    productType = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün türü (POS, SIM, vb.)", "example": "POS"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürüne ait seri numarası bilgisi", "example": ""})
    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürün modeli", "example": ""})
    orderType = fields.String(required=False, allow_none=False, metadata={"description": "İş emri kapsamında ürünle ilgili yapılan işlemin bilgisidir. ARIZA ve DEGISIM iş emirlerinde Payser tarafından geri alınan cihaz GERI_ALIM, verilen cihaz KURULUM olarak belirtilir.", "example": "KURULUM"})
    operationType = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kullanılacağı operasyon türünü belirtir.", "example": "EFTPOS"})
    operator = fields.String(required=False, allow_none=False, metadata={"description": "Kullanılacak SIM kartın operatör bilgisi", "example": ""})
    productStatus = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün durum bilgisi", "example": "SAGLAM"})
    image = fields.Url(required=False, allow_none=False, metadata={"description": "Ürüne görseline erişim yolu", "example": ""})
    accesories = fields.List(NestedModel("fsm.workorder.accesory"), required=False, allow_none=False, metadata={})


class GetWorkorderAddressService(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.address.service"

    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyeri yetkilisinin adı", "example": "İsim Soyisim"})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin birincil telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=False, allow_none=False, metadata={"description": "Üye işyerinin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    city = NestedModel("fsm.workorder.city", required=False, allow_none=False, metadata={})
    town = NestedModel("fsm.workorder.town", required=False, allow_none=False, metadata={})
    district = NestedModel("fsm.workorder.district", required=False, allow_none=False, metadata={})
    address = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyerinin UAVT kodu", "example": "34073041"})


class GetWorkorderMerchant(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.merchant"

    serviceAddress = NestedModel("fsm.getworkorder.address.service", required=False, allow_none=False, metadata={})


class GetWorkorderOrder(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.order"

    result = fields.String(required=False, allow_none=False, validate=validate.OneOf(["BASARILI", "BASARISIZ"]), metadata={"description": "İşlemin sonucu", "example": "BASARILI"})
    contactName = fields.String(required=False, allow_none=True, metadata={"description": "Hizmet verilen üye işyeri yetkilisinin adı", "example": "İsim Soyisim"})
    actionDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "İşlem tarihi", "example": "2024-03-19T18:45:01Z"})
    completeDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "Tamamlanma tarihi", "example": "2024-03-19T18:30:01Z"})


class GetWorkorderDelivery(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.delivery"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi takip numarası", "example": "PYS1242014041"})
    carrier = fields.String(required=False, allow_none=False, metadata={"description": "Taşıyıcı firmanın bilgisi", "example": "ABC Kargo"})
    promisedDate = fields.String(required=False, allow_none=True, metadata={"description": "Taahhüt edilen teslimat tarihi", "example": "2024-03-19T18:45:01Z"})
    transactionDate = fields.String(required=False, allow_none=True, metadata={"description": "İşlem tarihi", "example": "2024-03-19T18:45:01Z"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten kod", "example": "COLLECTED"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten mesaj", "example": ""})
    statusDetail = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumuna ilişkin detayların yer aldığı açıklama alanı. Gönderiye ilişkin açıklamalar bu alanda iletilir.", "example": "Teslim edildi - Merve A***** (Kendisi)"})
    transactionHistory = fields.List(NestedModel("fsm.workorder.transaction"), required=False, allow_none=False, metadata={})


class GetWorkorderDocument(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.document"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Dokümana ait tekil id bilgisi", "example": "36fe888b-a3c7-43a2-a086-c262e69cc50c"})
    documentType = fields.String(required=False, allow_none=False, metadata={"description": "Dokümana tip bilgisi", "example": "İşlem Takip Formu"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Dokümana ait Payser tarafından üretilmiş seri numarası", "example": "P-ITF-202403190942"})
    documentPath = fields.String(required=False, allow_none=False, metadata={"description": "Dokümana erişim/indirme için uri bilgisi", "example": "https://s3.payser.com.tr/36fe888b-a3c7-43a2-a086-c262e69cc50c.pdf"})


class GetWorkorderResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getworkorder.response"

    orderId = fields.String(required=False, allow_none=False, metadata={"description": "Payser tarafından oluşturulmuş iş emrine özel tekil ID bilgisi"})
    customerOrderId = fields.String(required=False, allow_none=None, metadata={"description": "İş emri için müşteri tarafından oluşturulmuş ID bilgisi"})
    orderType = fields.String(required=False, allow_none=False, metadata={"description": "İş emri tipi"})
    orderDescription = fields.String(required=False, allow_none=False, metadata={"description": "İş emri için müşterinin ilettiği detay bilgiler", "example": "Üye işyeri cihazının şarj olmadığını belirtmektedir."})
    createDate = fields.DateTime(required=False, allow_none=False, metadata={"description": "İş emrinin en son müdahale tarih saat bilgisi"})
    dueDate = fields.DateTime(required=False, allow_none=False, metadata={"description": "İş emrinin en son müdahale tarih saat bilgisi. SLA koşullarına göre sistem tarafından otomatik hesaplanır. İş emrinin BEKLEMEDE veya RANDEVU durumununa alınması halinde en son müdahale tarihi bilgisi güncellenir."})
    slaStatus = fields.String(required=False, allow_none=False, validate=validate.OneOf(["SLA_ICI", "SLA_DISI"]), metadata={"description": "İş emrinin SLA koşulları içinde veya dışında olduğu bilgisi. İş emrine en son müdahale tarihinden sonra müdahale edilmesi halinde SLA_DISI durumuna geçiş yapar."})
    project = NestedModel("fsm.workorder.project", required=False, allow_none=False, metadata={"example": "Müşteri tarafından projeli takip talep edilmesi halinde kullanılır. Açılacak tüm iş emirlerinde aynı id ve isim bilgisinin iletilmesi halinde bu iş emirleri Payser tarafından ayrı bir şekilde gruplanır ve raporlanır. SLA koşulları Payser ve Müşteri arasındaki mutabakat ile belirlenir ve son müdahale tarihleri elle güncellenir."})
    status = fields.String(required=False, allow_none=False, metadata={"description": "İş emri durumu"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "İş emri durumunun detayını belirten kod"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "İş emri durumunun detayını belirten mesaj"})
    statusDetail = fields.String(required=False, allow_none=False, metadata={"description": "İş emri durumunun detayını belirten açıklama"})
    serviceType = fields.String(required=False, allow_none=False, validate=validate.OneOf(["TEKNISYEN", "KARGO"]), metadata={"description": "İş emrine TEKNISYEN veya KARGO yoluyla hizmet verildiğini belirtir.", "example": "TEKNISYEN"})
    orderResult = NestedModel("fsm.getworkorder.order", required=False, allow_none=False, metadata={})
    rating = fields.String(required=False, allow_none=False, metadata={"description": "Üye işyeri geri bildirimi"})
    appointments = fields.List(NestedModel("fsm.workorder.appointment"), required=False, allow_none=False, metadata={})
    merchant = NestedModel("fsm.getworkorder.merchant", required=False, allow_none=False, metadata={"description": "Üye iş yerinin çağrı içinde iş ortağının ilettiği hizmet adresinden farklı bir adreste hizmet talep etmesi halinde kullanılır."})
    products = fields.List(NestedModel("fsm.getworkorder.product"), required=False, allow_none=False, metadata={})
    setup = NestedModel("fsm.workorder.setup", required=False, allow_none=False, metadata={})
    cargoDelivery = NestedModel("fsm.getworkorder.delivery", required=False, allow_none=False, metadata={"description": "İş emrine kargo aracılığıyla hizmet verilmesi halinde gönderiye ait hareket detaylarını içerir"})
    serviceDocuments = fields.List(NestedModel("fsm.getworkorder.document"), required=False, allow_none=False, metadata={})


class PostWorkorderApprovePath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approveworkorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Durumu onaylanmak veye sürdürülmek istenen iş emrinin ID bilgisi", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})


class PostWorkorderApproveRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approveworkorder.request"

    code = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "İşlem kodu", "example": "C1100"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "İşlem mesajı", "example": "Hizmet onaylandı"})


class PostWorkorderApproveResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approveworkorder.response"

    code = fields.String(required=False, allow_none=False, metadata={"description": "İşlem kodu", "example": "C1100"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "İşlem mesajı", "example": "Hizmet onaylandı"})


class PostWorkorderCancelPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.cancelworkorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "İptal etmek istediğiniz iş emrinin ID bilgisi", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})


class PostWorkorderCancelResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.cancelworkorder.response"

    code = fields.String(required=False, allow_none=False, metadata={"description": "İptal kodu", "example": ""})
    message = fields.String(required=False, allow_none=False, metadata={"description": "İptal mesajı", "example": ""})


class PostWorkorderWebhookRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.webhookworkorder.request"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Durum değişikliği gerçekleşen iş emrinin ID bilgisi", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})
    status = fields.String(required=False, allow_none=False, metadata={"description": "İş emrinin durumu", "example": "KAPALI"})
    updateDate = fields.DateTime(required=False, allow_none=False, metadata={"description": "İş emrinin durumunun değiştiği tarih", "example": "2024-03-19T19:03:01Z"})


class GetInventoryCityPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycity.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "İlin ID bilgisi"})


class GetInventoryCityList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycity.list"

    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün seri numarası", "example": "1000000001"})
    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün model bilgisi.", "example": "A910"})
    operatingSystem = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün işletim sistemini belirtir.", "example": "ANDROID"})
    owner = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün sahibi olan kurum", "example": "Kurum A"})
    subpartner = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kullanılacağı alt iş ortağı bilgisi", "example": "Operasyon B"})
    location = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün bulunduğu depo veya konumu belirtir.", "example": "Payser İzmir Depo / Arızalı"})


class GetInventoryCityRequest(Datamodel):

    _name = "fsm.getinventorycity.request"
    _inherit = "fsm.pagination.request"


class GetInventoryCityResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycity.response"
    _inherit = "fsm.pagination.response"

    products = fields.List(NestedModel("fsm.getinventorycity.list"), required=False, allow_none=False, metadata={})


class GetInventoryCityProductPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycityproduct.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "İlin ID bilgisi"})
    model = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Ürün model adı"})


class GetInventoryCityProductRequest(Datamodel):

    _name = "fsm.getinventorycityproduct.request"
    _inherit = "fsm.pagination.request"


class GetInventoryCityProductList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycityproduct.list"

    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün seri numarası", "example": "1000000001"})
    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün model bilgisi.", "example": "A910"})
    operatingSystem = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün işletim sistemini belirtir.", "example": "ANDROID"})
    owner = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün sahibi olan kurum", "example": "Kurum A"})
    subpartner = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün kullanılacağı alt iş ortağı bilgisi", "example": "Operasyon B"})
    location = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün bulunduğu depo veya konumu belirtir.", "example": "Payser İzmir Depo / Arızalı"})


class GetInventoryCityProductResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycityproduct.response"
    _inherit = "fsm.pagination.response"

    products = fields.List(NestedModel("fsm.getinventorycityproduct.list"), required=False, allow_none=False, metadata={})


class GetInventoryCityMaterialPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycitymaterial.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "İlin ID bilgisi"})
    model = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Malzeme adı"})


class GetInventoryCityMaterialRequest(Datamodel):

    _name = "fsm.getinventorycitymaterial.request"
    _inherit = "fsm.pagination.request"


class GetInventoryCityMaterialList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycitymaterial.list"

    name = fields.String(required=False, allow_none=False, metadata={"description": "Malzemenin Payser depolarında kayıtlı adı", "example": "Rulo Logolu"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Malzemeye Payser tarafından verilmiş seri numarası", "example": "PYS412401924"})
    count = fields.Integer(required=False, allow_none=False, metadata={"description": "Malzeme adedi", "example": 500})
    location = fields.String(required=False, allow_none=False, metadata={"description": "Malzemenin bulunduğu depo veya konumu belirtir.", "example": "Payser İstanbul Depo"})


class GetInventoryCityMaterialResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinventorycitymaterial.response"
    _inherit = "fsm.pagination.response"

    materials = fields.List(NestedModel("fsm.getinventorycitymaterial.list"), required=False, allow_none=False, metadata={})


class SaleorderCity(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.saleorder.city"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu ilin id bilgisi", "example": 34})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu ilin adı", "example": "İstanbul"})


class SaleorderTown(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.saleorder.town"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu ilçenin id bilgisi", "example": 1604})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu ilçenin adı", "example": "Sarıyer"})


class SaleorderDistrict(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.saleorder.district"

    id = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu mahallenin id bilgisi", "example": 34141})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin bulunduğu mahallenin adı", "example": "Maslak"})


class SaleorderProduct(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.saleorder.product"

    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün model bilgisi", "example": "Move5000F"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün seri veya sicil numarası"})


class PostSaleorderCreateAddressBilling(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.address.billing"

    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef yetkilisinin adı soyadı", "example": "İsim Soyisim"})
    identityNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin yetkili TCKN numarası.", "example": ""})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=False, allow_none=False, metadata={"description": "Mükellefin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    tradeRegistrationNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin ticaret sicil numarası", "example": "123456-0"})
    city = NestedModel("fsm.saleorder.city", required=False, allow_none=False, metadata={})
    town = NestedModel("fsm.saleorder.town", required=False, allow_none=False, metadata={})
    district = NestedModel("fsm.saleorder.district", required=False, allow_none=False, metadata={})
    address = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin UAVT kodu", "example": "34073041"})


class PostSaleorderApproveCreateShipping(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.address.shipping"

    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Teslim alacak kişinin adı soyadı", "example": "İsim Soyisim"})
    identityNumber = fields.String(required=False, allow_none=False, metadata={"description": "Teslim alacak kişinin TCKN numarası.", "example": ""})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=False, allow_none=False, metadata={"description": "Mükellefin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    tradeRegistrationNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin ticaret sicil numarası", "example": "123456-0"})
    city = NestedModel("fsm.saleorder.city", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    town = NestedModel("fsm.saleorder.town", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={})
    district = NestedModel("fsm.saleorder.district", required=False, allow_none=False, metadata={})
    address = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin UAVT kodu", "example": "34073041"})


class PostSaleorderApproveDetail(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.detail"

    key = fields.String(required=True, allow_none=False, metadata={"description": "Detay anahtarı.", "example": "Barcode"})
    value = fields.String(required=True, allow_none=True, metadata={"description": "Detay değeri.", "example": "XYZ"})


class PostSaleorderCreateCustomer(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.customer"

    isCompany = fields.Boolean(required=False, allow_none=False, metadata={"description": "Mükellef tüzel kişilik ise bu alan True olarak girilir. Varsayılan olarak False gerçek kişidir.", "example": True})
    name = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef unvanı", "example": "ABC Ticaret Ltd. Şti."})
    tableName = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef tabela adı", "example": "Flora Çiçekçilik"})
    taxNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef VKN veya TCKN. VKN iletilmesi halinde 10 karakter, TCKN iletilmesi halinde 11 karakter olmalıdır.", "example": "5205906683"})
    taxOffice = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef vergi dairesi. Vergi dairesinin adı iletilirken Vergi Dairesi, V.D., Mal Md. gibi ibareler eklenmemelidir.", "example": "MASLAK"})
    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin yetkili adı soyadı", "example": ""})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin telefon numarası", "example": ""})
    mobileNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil numarası", "example": ""})
    email = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin e-posta adresi", "example": ""})
    billingAddress = NestedModel("fsm.createsaleorder.address.billing", required=False, allow_none=False, metadata={"description": "Mükellefin fatura adresi"})
    shippingAddress = NestedModel("fsm.createsaleorder.address.shipping", required=False, allow_none=False, metadata={"description": "Mükellefin teslimat adresi. Ürünün rezerve edileceği deponun belirlenmesi için il alanı zorunlu olarak iletilmeldir."})


class PostSaleorderCreateProduct(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.product"

    model = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Ürünün model bilgisi", "example": "Move5000F"})
    quantity = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Siparişte yer alması istenen ürünün miktar bilgisi. Tek siparişte en fazla 99 adet ürün rezerve edilebilir.", "example": 1})


class PostSaleorderCreateRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.request"

    customerOrderId = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş için müşteri tarafından oluşturulmuş id bilgisi", "example": "b5c9f785-ea6d-4998-ae69-9709c553e1db"})
    channel = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Satışın yapıldığı kanalın bilgisi"})
    customer = NestedModel("fsm.createsaleorder.customer", required=False, allow_none=False, metadata={})
    products = fields.List(NestedModel("fsm.createsaleorder.product"), required=False, allow_none=False, metadata={})


class PostSaleorderCreateResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.createsaleorder.response"

    orderId = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş için Payser tarafından oluşturulmuş ID bilgisi. Oluşturulan sipariş, bu ID bilgisi ile approveSaleOrder servisi kullanılarak onaylanır."})
    customerOrderId = fields.String(required=False, allow_none=True, metadata={"description": "Sipariş için müşteri tarafından oluşturulmuş ID bilgisi"})
    products = fields.List(NestedModel("fsm.saleorder.product"), required=False, allow_none=False, metadata={})


class PostSaleorderApprovePath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Sipariş için Payser tarafından oluşturulmuş id bilgisi", "example": "dd1fb948-f6a8-4534-bfec-9454c58be89e"})


class PostSaleorderApproveAddressBilling(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.address.billing"

    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef yetkilisinin adı soyadı", "example": "İsim Soyisim"})
    identityNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin yetkili TCKN numarası.", "example": ""})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=False, allow_none=False, metadata={"description": "Mükellefin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    tradeRegistrationNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin ticaret sicil numarası", "example": "123456-0"})
    city = NestedModel("fsm.saleorder.city", required=False, allow_none=False, metadata={})
    town = NestedModel("fsm.saleorder.town", required=False, allow_none=False, metadata={})
    district = NestedModel("fsm.saleorder.district", required=False, allow_none=False, metadata={})
    address = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin UAVT kodu", "example": "34073041"})


class PostSaleorderApproveAddressShipping(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.address.shipping"

    contactName = fields.String(required=False, allow_none=False, metadata={"description": "Teslim alacak kişinin adı soyadı", "example": "İsim Soyisim"})
    identityNumber = fields.String(required=False, allow_none=False, metadata={"description": "Teslim alacak kişinin TCKN numarası.", "example": ""})
    phoneNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin telefon numarası (10 hane)", "example": "212XXXYYZZ"})
    mobile = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil telefon numarası (10 hane)", "example": "5XXYYYZZZZ"})
    email = fields.Email(required=False, allow_none=False, metadata={"description": "Mükellefin e-posta adresi", "example": "isim@alanadi.com"})
    mersisNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin MERSİS numarası (16 hane)", "example": "1111222233334444"})
    tradeRegistrationNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin ticaret sicil numarası", "example": "123456-0"})
    city = NestedModel("fsm.saleorder.city", required=False, allow_none=False, metadata={})
    town = NestedModel("fsm.saleorder.town", required=False, allow_none=False, metadata={})
    district = NestedModel("fsm.saleorder.district", required=False, allow_none=False, metadata={})
    address = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin bulunduğu cadde, sokak, bina numarası, iç kapı numarası, vb. adresi", "example": "Eski Büyükdere Cd., No:9, İz Plaza Giz, Kat:giris"})
    zipCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin posta kodu", "example": "34485"})
    latitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin enlem bilgisi", "example": "41.109046"})
    longitude = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin boylam bilgisi", "example": "29.015626"})
    uavtCode = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin UAVT kodu", "example": "34073041"})


class PostSaleorderApproveCustomer(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.customer"

    isCompany = fields.Boolean(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellef tüzel kişilik ise bu alan True olarak girilir. Varsayılan olarak False gerçek kişidir.", "example": True})
    name = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellef unvanı", "example": "ABC Ticaret Ltd. Şti."})
    tableName = fields.String(required=False, allow_none=False, metadata={"description": "Mükellef tabela adı", "example": "Flora Çiçekçilik"})
    taxNumber = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellef VKN veya TCKN. VKN iletilmesi halinde 10 karakter, TCKN iletilmesi halinde 11 karakter olmalıdır.", "example": "5205906683"})
    taxOffice = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellef vergi dairesi. Vergi dairesinin adı iletilirken Vergi Dairesi, V.D., Mal Md. gibi ibareler eklenmemelidir.", "example": "MASLAK"})
    contactName = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin yetkili adı soyadı", "example": ""})
    phoneNumber = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin telefon numarası", "example": ""})
    mobileNumber = fields.String(required=False, allow_none=False, metadata={"description": "Mükellefin mobil numarası", "example": ""})
    email = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin e-posta adresi", "example": ""})
    billingAddress = NestedModel("fsm.approvesaleorder.address.billing", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin fatura adresi"})
    shippingAddress = NestedModel("fsm.approvesaleorder.address.shipping", required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Mükellefin teslimat adresi. Ürünün rezerve edileceği deponun belirlenmesi için il alanı zorunlu olarak iletilmeldir."})
    details = fields.List(NestedModel("fsm.approvesaleorder.detail"), required=False, allow_none=False, metadata={"description": "Sipariş detayı."})


class PostSaleorderApproveRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.request"

    customerOrderId = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş için müşteri tarafından oluşturulmuş id bilgisi", "example": "b5c9f785-ea6d-4998-ae69-9709c553e1db"})
    channel = fields.String(required=False, allow_none=False, metadata={"description": "Satışın yapıldığı kanalın bilgisi"})
    customer = NestedModel("fsm.approvesaleorder.customer", required=False, allow_none=False, metadata={})


class PostSaleorderApproveResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.approvesaleorder.response"

    orderId = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş için Payser tarafından oluşturulmuş ID bilgisi."})
    customerOrderId = fields.String(required=False, allow_none=True, metadata={"description": "Sipariş için müşteri tarafından oluşturulmuş ID bilgisi"})
    products = fields.List(NestedModel("fsm.saleorder.product"), required=False, allow_none=False, metadata={})


class PostSaleorderCancelPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.cancelsaleorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Siparişin ID bilgisi"})


class PostSaleorderCancelList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.cancelsaleorder.list"

    code = fields.String(required=False, allow_none=False, metadata={"description": "Durum kodu", "example": "C1073"})
    message = fields.String(required=False, allow_none=False, metadata={"description": "Durum mesajı", "example": "Sipariş iş ortağı tarafından iptal edildi"})


class PostSaleorderCancelResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.cancelsaleorder.response"

    errors = fields.List(NestedModel("fsm.cancelsaleorder.list"), required=False, allow_none=False, metadata={})


class GetSaleorderQueryPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getsaleorder.path"

    orderId = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Siparişin ID bilgisi"})


class GetSaleorderQueryTransaction(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getsaleorder.transaction"

    transactionDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "İşlem tarihi", "example": "2024-03-19T18:45:01Z"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten kod", "example": "COLLECTED"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten mesaj", "example": ""})
    statusDetail = fields.String(required=False, allow_none=False, metadata={"description": "İşlem açıklaması", "example": "Teslim edildi - Merve A***** (Kendisi)"})
    nonDeliveryReason = fields.String(required=False, allow_none=True, metadata={"description": "Teslim edilmeme sebebi", "example": "REFUSED"})
    nonDeliveryReasonMessage = fields.String(required=False, allow_none=True, metadata={"description": "İşlem edilmeme sebebi açıklaması", "example": "Alıcı Kabul Etmiyor"})


class GetSaleorderQueryDelivery(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getsaleorder.delivery"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi takip numarası", "example": "PYS1242014041"})
    carrier = fields.String(required=False, allow_none=False, metadata={"description": "Taşıyıcı firmanın bilgisi", "example": "ABC Kargo"})
    promisedDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "Taahhüt edilen teslimat tarihi", "example": "2024-03-19T18:45:01Z"})
    transactionDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "İşlem tarihi", "example": "2024-03-19T18:45:01Z"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten kod", "example": "COLLECTED"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumunu belirten mesaj", "example": ""})
    statusDetail = fields.String(required=False, allow_none=False, metadata={"description": "Gönderi durumuna ilişkin detayların yer aldığı açıklama alanı. Gönderiye ilişkin açıklamalar bu alanda iletilir.", "example": "Teslim edildi - Merve A***** (Kendisi)"})
    transactionHistory = fields.List(NestedModel("fsm.getsaleorder.transaction"), required=False, allow_none=False, metadata={})


class GetSaleorderQueryProduct(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getsaleorder.product"

    model = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün model bilgisi", "example": "Move5000F"})
    serialNumber = fields.String(required=False, allow_none=False, metadata={"description": "Ürünün seri veya sicil numarası"})
    status = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş durumu", "example": "TEKLİF"})
    statusCode = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş durumunu belirten kod"})
    statusMessage = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş durumunu belirten mesaj"})
    delivery = NestedModel("fsm.getsaleorder.delivery", required=False, allow_none=False, metadata={"description": "Siparişe kargo aracılığıyla hizmet verilmesi halinde gönderiye ait hareket detaylarını içerir"})


class GetSaleorderQueryResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getsaleorder.response"

    orderId = fields.String(required=False, allow_none=False, metadata={"description": "Sipariş için Payser tarafından oluşturulmuş ID bilgisi."})
    customerOrderId = fields.String(required=False, allow_none=True, metadata={"description": "Sipariş için müşteri tarafından oluşturulmuş ID bilgisi"})
    products = fields.List(NestedModel("fsm.getsaleorder.product"), required=False, allow_none=False, metadata={})


class GetInfoOrdertypeRequest(Datamodel):

    _name = "fsm.getinfoordertype.request"
    _inherit = "fsm.pagination.request"


class GetInfoOrdertypeList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfoordertype.list"

    name = fields.String(required=False, allow_none=False, metadata={"description": "İş emri türleri", "example": "KURULUM"})


class GetInfoOrdertypeResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfoordertype.response"
    _inherit = "fsm.pagination.response"

    #orderTypes = fields.List(fields.String, required=False, allow_none=False, metadata={"description": "İş emri türleri", "example": ["KURULUM", "ARIZA", "ONARIM"]})
    orderTypes = fields.List(NestedModel("fsm.getinfoordertype.list"), required=False, allow_none=False, metadata={})


class GetInfoProjectRequest(Datamodel):

    _name = "fsm.getinfoproject.request"
    _inherit = "fsm.pagination.request"


class GetInfoProjectList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfoproject.list"

    id = fields.UUID(required=False, allow_none=False, metadata={"description": "Çağrının ait olduğu projenin tekil ID bilgisi", "example": "c4249f1c-efe9-4340-a1b5-d0f27817b3a0"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "Çağrının ait olduğu projenin isim bilgisi", "example": "Sadakat Kart Projesi"})
    sla = fields.String(required=False, allow_none=False, metadata={"description": "Projeye ait SLA koşulu", "example": "YEDI_GUN"})
    maximumCount = fields.Integer(required=False, allow_none=False, metadata={"description": "Proje kapsamında oluşturulabilecek maksimum iş emri adedi", "example": 1000})
    dateStart = fields.Date(required=False, allow_none=False, metadata={"description": "Proje başlangıç tarihi"})
    dateEnd = fields.Date(required=False, allow_none=False, metadata={"description": "Proje bitiş tarihi"})


class GetInfoProjectResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfoproject.response"
    _inherit = "fsm.pagination.response"

    projects = fields.List(NestedModel("fsm.getinfoproject.list"), required=False, allow_none=False, metadata={})


class GetInfoSubpartnerRequest(Datamodel):

    _name = "fsm.getinfosubpartner.request"
    _inherit = "fsm.pagination.request"


class GetInfoSubpartnerList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfosubpartner.list"

    name = fields.String(required=False, allow_none=False, metadata={"description": "Alt iş ortağının isim bilgisi", "example": "IS_ORTAGI_A"})


class GetInfoSubpartnerResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfosubpartner.response"
    _inherit = "fsm.pagination.response"

    subpartners = fields.List(NestedModel("fsm.getinfosubpartner.list"), required=False, allow_none=False, metadata={})


class GetInfoCityRequest(Datamodel):

    _name = "fsm.getinfocity.request"
    _inherit = "fsm.pagination.request"


class GetInfoCityList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfocity.list"

    id = fields.Integer(required=False, allow_none=False, metadata={"description": "İlin ID bilgisi"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "İlin isim bilgisi"})


class GetInfoCityResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfocity.response"
    _inherit = "fsm.pagination.response"

    cities = fields.List(NestedModel("fsm.getinfocity.list"), required=False, allow_none=False, metadata={})


class GetInfoTownPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotown.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Hizmet detayları sorgulanan ilin ID bilgisi"})


class GetInfoTownRequest(Datamodel):

    _name = "fsm.getinfotown.request"
    _inherit = "fsm.pagination.request"


class GetInfoTownList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotown.list"

    id = fields.Integer(required=False, allow_none=False, metadata={"description": "İlçenin ID bilgisi"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "İlçenin isim bilgisi"})


class GetInfoTownResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotown.response"
    _inherit = "fsm.pagination.response"

    towns = fields.List(NestedModel("fsm.getinfotown.list"), required=False, allow_none=False, metadata={})


class GetInfoDistrictPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfodistrict.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Hizmet detayları sorgulanan ilin ID bilgisi"})
    townId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Hizmet detayları sorgulanan ilçenin ID bilgisi"})


class GetInfoDistrictRequest(Datamodel):

    _name = "fsm.getinfodistrict.request"
    _inherit = "fsm.pagination.request"


class GetInfoDistrictList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfodistrict.list"

    id = fields.Integer(required=False, allow_none=False, metadata={"description": "Mahallenin ID bilgisi"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "Mahallenin isim bilgisi"})


class GetInfoDistrictResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfodistrict.response"
    _inherit = "fsm.pagination.response"

    districts = fields.List(NestedModel("fsm.getinfodistrict.list"), required=False, allow_none=False, metadata={})


class GetInfoZonePath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfozone.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Hizmet detayları sorgulanan ilin ID bilgisi"})
    townId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Hizmet detayları sorgulanan ilçenin ID bilgisi"})


class GetInfoZoneRequest(Datamodel):

    _name = "fsm.getinfozone.request"
    _inherit = "fsm.pagination.request"


class GetInfoZoneTown(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfozone.town"

    id = fields.Integer(required=False, allow_none=False, metadata={"description": "İlçenin ID bilgisi"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "İlçenin isim bilgisi"})
    agreementName = fields.String(required=False, allow_none=False, metadata={"description": "Sözleşme Adı"})
    serviceType = fields.String(required=False, allow_none=False, validate=validate.OneOf(["TEKNISYEN", "KARGO"]), metadata={"description": "Hizmetin türü belirtir. Teknisyen hizmet bölgelerinde TEKNISYEN, kargo yoluyla hizmet verilen bölgelerde KARGO olarak belirtilir.", "example": "TEKNISYEN"})
    serviceLevel = fields.String(required=False, allow_none=False, metadata={"description": "Taahhüt edilen hizmet seviyesini belirtir", "example": "24"})


class GetInfoZoneResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfozone.response"
    _inherit = "fsm.pagination.response"

    towns = fields.List(NestedModel("fsm.getinfozone.town"), required=False, allow_none=False, metadata={})


class GetInfoTaxofficePath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotaxoffice.path"

    cityId = fields.Integer(required=True, allow_none=False, validate=validate.NoneOf([""]), dump_default=0, metadata={"description": "Vergi daireleri sorgulanan ilin ID bilgisi"})


class GetInfoTaxofficeRequest(Datamodel):

    _name = "fsm.getinfotaxoffice.request"
    _inherit = "fsm.pagination.request"


class GetInfoTaxofficeList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotaxoffice.list"

    id = fields.String(required=False, allow_none=False, metadata={"description": "Vergi dairesinin GİB tarafından belirlenmiş kod bilgisi"})
    name = fields.String(required=False, allow_none=False, metadata={"description": "Vergi dairesinin isim bilgisi"})


class GetInfoTaxofficeResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfotaxoffice.response"
    _inherit = "fsm.pagination.response"

    taxoffices = fields.List(NestedModel("fsm.getinfotaxoffice.list"), required=False, allow_none=False, metadata={})


class GetInfoStatuscodeRequest(Datamodel):

    _name = "fsm.getinfostatuscode.request"
    _inherit = "fsm.pagination.request"


class GetInfoStatuscodeList(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfostatuscode.list"

    code = fields.String(required=False, allow_none=True, metadata={"description": "Durum kodu", "example": "C1000"})
    message = fields.String(required=False, allow_none=True, metadata={"description": "Durum Açıklaması", "example": "İş emri oluşturuldu"})
    httpCode = fields.Integer(required=False, allow_none=True, metadata={"description": "Durum HTTP Kodu", "example": 200})


class GetInfoStatuscodeResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.getinfostatuscode.response"
    _inherit = "fsm.pagination.response"

    statuscodes = fields.List(NestedModel("fsm.getinfostatuscode.list"), required=False, allow_none=False, metadata={})


class DownloadDeliveryContractPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.downloaddeliverycontract.path"

    reference = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Gönderi Takip Referansı", "example": "PRP1234567890"})


class UploadDeliveryContractPath(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.uploaddeliverycontract.path"

    reference = fields.String(required=True, allow_none=False, validate=validate.NoneOf([""]), metadata={"description": "Gönderi Takip Referansı", "example": "PRP1234567890"})


class UploadDeliveryContractRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "fsm.uploaddeliverycontract.request"
    _inherit = "fsm.request.0"
