# -*- coding: utf-8 -*-
import re
import json
import base64
import logging
import traceback
from lxml import etree
from urllib.parse import urlparse
from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import request, route, Response, Controller, STATIC_CACHE

from ..services.soap import FsmSoap as Soap, NAMESPACES
from ..response import Response400, Response401, Response404

_logger = logging.getLogger(__name__)

#SOAP_TNS = 'https://%s/api/proxy/%s/'
SOAP_TNS = 'http://tempuri.org/'

class FsmApiProxyController(Controller):

    @route(['/api/proxy/<proxy>'], type='http', methods=['GET', 'POST'], auth='public', csrf=False, save_session=False)
    def api_proxy(self, proxy, **kw):
        proxy = request.env['fsm.api.proxy'].sudo().search([('code', '=', proxy)], limit=1)
        if not proxy:
            raise NotFound()

        try:
            if request.httprequest.method == 'GET':
                refs = {}
                for service in proxy.service_ids:
                    input = service.get_json_schema('input')
                    output = service.get_json_schema('output')
                    refs[service.soap_ref] = {'input': input, 'output': output}

                if proxy.type == 'rest':
                    pass
                elif proxy.type == 'soap':
                    data = f"""<wsdl:definitions xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:tns="http://tempuri.org/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:http="http://schemas.microsoft.com/ws/06/2004/policy/http" xmlns:msc="http://schemas.microsoft.com/ws/2005/12/wsdl/contract" xmlns:wsp="http://schemas.xmlsoap.org/ws/2004/09/policy" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsam="http://www.w3.org/2007/05/addressing/metadata" targetNamespace="http://tempuri.org/" name="IPayserService" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
  <wsdl:types>
    <xsd:schema elementFormDefault="qualified" targetNamespace="http://tempuri.org/">
      <xsd:import namespace="http://schemas.microsoft.com/2003/10/Serialization/Arrays" />
      <xsd:import namespace="http://schemas.datacontract.org/2004/07/System" />
      <xsd:element name="createWorkorder">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="userName" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="password" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="talepNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="bildirenBankaKodu" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="bankaTalepNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="talepTipi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="cagriArizaSebebi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="musteriUiyNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="musteriUiyTerminalNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="uiyNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="uiyTerminalNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyUnvaniAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyAdresi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyIlcesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyIli" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyYetkiliAd" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyYetkiliSoyad" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyYetkiliUnvani" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyVergiDairesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyVergiNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyTel1" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyTel2" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyGsmTel" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyEmail" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyMersisNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyTicaretSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="mukellefUiyEsnafSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriYeriFarkli" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyUnvaniAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyAdresi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyIlcesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyIli" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyYetkiliAd" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyYetkiliSoyad" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyYetkiliUnvani" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyVergiDairesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyVergiNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyTel1" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyTel2" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyGsmTel" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyEmail" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyMersisNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyTicaretSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="altMusteriUiyEsnafSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriFarkli" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyUnvaniAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyAdresi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyIlcesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyIli" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyYetkiliAd" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyYetkiliSoyad" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyYetkiliUnvani" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyVergiDairesi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyVergiNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyTel1" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyTel2" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyGsmTel" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyEmail" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyMersisNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyTicaretSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="hizmetYeriUiyEsnafSicilNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="cagriAciklama" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="musteriOnceligi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="bankaSubeKodu" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="sektor" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="cihazModel" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="cihazSeriNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="uygulamaVersiyonNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="talebiIletenKullanici" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="projeAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="garantiKapsaminda" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="yeniUyeNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="yeniTermNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="yeniFirmaAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="channelinfo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="stockstate" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="billingstate" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="cargodate" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="sicilno" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="izinYazisiTarihi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="bankaSiparisNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="RFU1" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="RFU2" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="RFU3" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="RFU4" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="RFU5" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="ProjeBaslangicTarihi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="ProjeGunSayisi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="aksesuar" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="createWorkorderResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="createWorkorderResult" type="tns:createWorkorderResponseInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="queryWorkorder">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="userName" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="password" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="requestId" type="xsd:string" />
            <xsd:element minOccurs="1" maxOccurs="1" name="requestedState" type="xsd:int" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="queryWorkorderResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="queryWorkorderResult" type="tns:queryWorkorderResponseInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="approveWorkorder">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="userName" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="password" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="approveWoInfoList" nillable="true" type="tns:ArrayOfapproveWorkorderInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="approveWorkorderResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="approveWorkorderResult" type="tns:approveWorkorderResponseInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="cancelWorkorder">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="userName" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="password" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="requestId" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="talepTipi" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="cancelWorkorderResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="cancelWorkorderResult" type="tns:cancelWorkorderResponseInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="processAsset">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="userName" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="password" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="seriNo" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="depoAdi" type="xsd:string" />
            <xsd:element minOccurs="0" maxOccurs="1" name="islemTuru" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="processAssetResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element minOccurs="0" maxOccurs="1" name="processAssetResult" type="tns:processAssetResponseInfo" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:complexType name="createWorkorderResponseInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="stateResponse" type="tns:stateResponse" />
          <xsd:element minOccurs="0" maxOccurs="1" name="talepNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="wonum" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="olusanEmirler" type="tns:KeyValueParentModel" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="queryWorkorderResponseInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="message" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="moreRecord" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="queryWorkorderResult" nillable="true" type="tns:ArrayOfqueryWorkorderResult" />
          <xsd:element minOccurs="0" maxOccurs="1" name="stateResponse" type="tns:stateResponse" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfapproveWorkorderInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="unbounded" nillable="true" name="approveWorkorderInfo" type="tns:approveWorkorderInfo" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="approveWorkorderResponseInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="approveWoResultListField" nillable="true" type="tns:ArrayOfapproveWorkorderInfo" />
          <xsd:element minOccurs="0" maxOccurs="1" name="stateResponseField" type="tns:stateResponse" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="cancelWorkorderResponseInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="stateResponseField" type="tns:stateResponse" />
          <xsd:element minOccurs="0" maxOccurs="1" name="talepNoField" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="wonumField" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="processAssetResponseInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="seriNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="stateResponse" type="tns:stateResponse" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="stateResponse">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="stateMessage" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="stateValue" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="KeyValueParentModel">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="KeyValueList" nillable="true" type="tns:ArrayOfKeyValueParentItem" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfqueryWorkorderResult">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="unbounded" nillable="true" name="queryWorkorderResult" type="tns:queryWorkorderResult" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="approveWorkorderInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="talepNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="woStateMessage" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="woStateValue" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfKeyValueParentItem">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="unbounded" nillable="true" name="KeyValueParentItem" type="tns:KeyValueParentItem" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="queryWorkorderResult">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="formNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="gsmNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="gsmSimNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="hizmetAlanKisi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="kullanilanDegistirilenMalzemeler" nillable="true" type="tns:ArrayOfmaterialInfo" />
          <xsd:element minOccurs="0" maxOccurs="1" name="mudahaleTarihi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="tamamlanmaTarihi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="ortakBankaIslem" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="randevuMudahaleTarih" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="randevuSebebi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="randevuVerenKisi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="randevuVerilenTarih" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="sahafirmasiCagriNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="sahafirmasiBolgesi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="talepNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="talepStatusu" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="teknikUzman" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="varlikDurumu" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="yapilanIslem" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="yapilanIslemAciklama" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="olumluOlumsuz" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="teknikUzmanTCKN" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="talepTipi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="kargoNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="kargoFirmasi" type="xsd:string" />
          <xsd:element minOccurs="1" maxOccurs="1" name="kargolanacak" type="xsd:boolean" />
          <xsd:element minOccurs="0" maxOccurs="1" name="doc" nillable="true" type="tns:ArrayOfDocumentToTask" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="KeyValueParentItem">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="TalepTipi" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="TalepNo" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="ParentID" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfmaterialInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="unbounded" nillable="true" name="materialInfo" type="tns:materialInfo" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfDocumentToTask">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="unbounded" nillable="true" name="DocumentToTask" type="tns:DocumentToTask" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="materialInfo">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="malzemeIslem" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="malzemeKod" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="DocumentToTask">
        <xsd:sequence>
          <xsd:element minOccurs="0" maxOccurs="1" name="fileContent" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="fileExtension" type="xsd:string" />
          <xsd:element minOccurs="0" maxOccurs="1" name="fileName" type="xsd:string" />
        </xsd:sequence>
      </xsd:complexType>
    </xsd:schema>
  </wsdl:types>
  <wsdl:message name="IPayserService_createWorkorder_InputMessage">
    <wsdl:part name="parameters" element="tns:createWorkorder" />
  </wsdl:message>
  <wsdl:message name="IPayserService_createWorkorder_OutputMessage">
    <wsdl:part name="parameters" element="tns:createWorkorderResponse" />
  </wsdl:message>
  <wsdl:message name="IPayserService_queryWorkorder_InputMessage">
    <wsdl:part name="parameters" element="tns:queryWorkorder" />
  </wsdl:message>
  <wsdl:message name="IPayserService_queryWorkorder_OutputMessage">
    <wsdl:part name="parameters" element="tns:queryWorkorderResponse" />
  </wsdl:message>
  <wsdl:message name="IPayserService_approveWorkorder_InputMessage">
    <wsdl:part name="parameters" element="tns:approveWorkorder" />
  </wsdl:message>
  <wsdl:message name="IPayserService_approveWorkorder_OutputMessage">
    <wsdl:part name="parameters" element="tns:approveWorkorderResponse" />
  </wsdl:message>
  <wsdl:message name="IPayserService_cancelWorkorder_InputMessage">
    <wsdl:part name="parameters" element="tns:cancelWorkorder" />
  </wsdl:message>
  <wsdl:message name="IPayserService_cancelWorkorder_OutputMessage">
    <wsdl:part name="parameters" element="tns:cancelWorkorderResponse" />
  </wsdl:message>
  <wsdl:message name="IPayserService_processAsset_InputMessage">
    <wsdl:part name="parameters" element="tns:processAsset" />
  </wsdl:message>
  <wsdl:message name="IPayserService_processAsset_OutputMessage">
    <wsdl:part name="parameters" element="tns:processAssetResponse" />
  </wsdl:message>
  <wsdl:portType name="IPayserService">
    <wsdl:operation name="createWorkorder">
      <wsdl:input message="tns:IPayserService_createWorkorder_InputMessage" />
      <wsdl:output message="tns:IPayserService_createWorkorder_OutputMessage" />
    </wsdl:operation>
    <wsdl:operation name="queryWorkorder">
      <wsdl:input message="tns:IPayserService_queryWorkorder_InputMessage" />
      <wsdl:output message="tns:IPayserService_queryWorkorder_OutputMessage" />
    </wsdl:operation>
    <wsdl:operation name="approveWorkorder">
      <wsdl:input message="tns:IPayserService_approveWorkorder_InputMessage" />
      <wsdl:output message="tns:IPayserService_approveWorkorder_OutputMessage" />
    </wsdl:operation>
    <wsdl:operation name="cancelWorkorder">
      <wsdl:input message="tns:IPayserService_cancelWorkorder_InputMessage" />
      <wsdl:output message="tns:IPayserService_cancelWorkorder_OutputMessage" />
    </wsdl:operation>
    <wsdl:operation name="processAsset">
      <wsdl:input message="tns:IPayserService_processAsset_InputMessage" />
      <wsdl:output message="tns:IPayserService_processAsset_OutputMessage" />
    </wsdl:operation>
  </wsdl:portType>
  <wsdl:binding name="BasicHttpBinding" type="tns:IPayserService" style="document">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http" />
    <wsdl:operation name="createWorkorder">
      <soap:operation soapAction="http://tempuri.org/IPayserService/createWorkorder" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="queryWorkorder">
      <soap:operation soapAction="http://tempuri.org/IPayserService/queryWorkorder" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="approveWorkorder">
      <soap:operation soapAction="http://tempuri.org/IPayserService/approveWorkorder" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="cancelWorkorder">
      <soap:operation soapAction="http://tempuri.org/IPayserService/cancelWorkorder" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="processAsset">
      <soap:operation soapAction="http://tempuri.org/IPayserService/processAsset" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
  </wsdl:binding>
  <wsdl:service name="IPayserService">
    <wsdl:port name="BasicHttpBinding" binding="tns:BasicHttpBinding">
      <soap:address location="{request.httprequest.url}" />
    </wsdl:port>
  </wsdl:service>
</wsdl:definitions>"""
                    headers = [('Content-Type', 'text/xml; charset=utf-8'), ('Cache-Control', 'max-age=%s' % STATIC_CACHE)]
                    return request.make_response(data, headers)
                    ns = {**NAMESPACES['wsdl']}
                    url = urlparse(request.httprequest.url)
                    ns['tns'] = SOAP_TNS % (url.netloc, proxy.code)

                    root = etree.Element('{%s}definitions' % ns['wsdl'], {'targetNamespace': ns['tns']}, nsmap=ns)
                    Soap._soap_add_types(root, refs, ns)
                    Soap._soap_add_messages(root, refs, ns)
                    Soap._soap_add_ports(root, refs, ns)
                    Soap._soap_add_bindings(root, refs, ns)
                    Soap._soap_add_services(root, ns)

                    data = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
                    headers = [('Content-Type', 'text/xml; charset=utf-8'), ('Cache-Control', 'max-age=%s' % STATIC_CACHE)]
                    #return request.make_response(json.dumps(refs, indent=4), headers)
                    return request.make_response(data, headers)
                return Response('OK', status=200)

            else:
                if proxy.type == 'rest':
                    pass
                elif proxy.type == 'soap':
                    data = request.httprequest.get_data()
                    url = urlparse(request.httprequest.url)
                    #address = SOAP_TNS % (url.netloc, proxy.code)
                    address = SOAP_TNS
                    root = etree.fromstring(data)
                    item = root.xpath('//ns:*', namespaces={'ns': address})[0]
                    method = etree.QName(item.tag).localname
                    #method = re.sub(r'(.*)Request', r'\g<1>', etree.QName(item.tag).localname)
                    params = Soap._soap_get_params(item)

                    service = request.env['fsm.api.proxy.service'].sudo().search([('proxy_id', '=', proxy.id), ('soap_ref', '=', method)], limit=1)
                    if not service:
                        raise Response404(None)

                    status, response = service._execute(params)
                    result = Soap._soap_get_response(method, address, response)
                    headers = [
                        ('MIME-Version', '1.0'),
                        ('Cache-Control', 'no-store'),
                        ('Content-Type', 'text/xml; charset=utf-8'),
                        #('Content-Type', 'multipart/related; type="text/xml"; charset=utf-8; start="<Body>"'),
                    ]
                    #service.service_id.with_context(no_log=False)._log({**log, 'res': result})
                    return Response(result, status=status, headers=headers)

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
