# -*- coding: utf-8 -*-
from odoo import models, fields


class FsmTask(models.Model):
    _inherit = 'fsm.task'

    api_log_worldline_id = fields.Many2one('fsm.api.log.worldline', string='Worldline API Log', readonly=True)
    api_log_worldline_bank_code = fields.Char(related='api_log_worldline_id.bildirenBankaKodu', string='Worldline Bank Code')
    api_log_worldline_channel_info = fields.Char(related='api_log_worldline_id.channelinfo', string='Worldline Channel Info')
    proxy_code_worldline_read = fields.Boolean(string='Worldline API Read', readonly=True)
    proxy_code_worldline_write_date = fields.Datetime(string='Worldline API Write Date', readonly=True)
    field_api_log_worldline_bank_code = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_api_log_worldline_channel_info = fields.Integer(compute='_compute_fields', compute_sudo=True)

    def write(self, values):
        if 'flow_stage_id' in values:
            tasks = {}
            for task in self:
                if task.api_log_worldline_id:
                    tasks.update({task.id: task.stage_id.code})
        res = super().write(values)
        if 'flow_stage_id' in values:
            for task in self:
                if task.api_log_worldline_id:
                    if task.id in tasks and tasks[task.id] != task.stage_id.code:
                        task.write({
                            'proxy_code_worldline_read': False,
                            'proxy_code_worldline_write_date': fields.Datetime.now(),
                        })
        return res

    def create_api_log(self):
        proxy = self.env.context.get('proxy')
        if proxy and proxy.code == 'worldline':
            banks = {b.code: b.name for b in proxy.bank_ids}
            statuses = {s.code: s.name for s in proxy.status_ids}
            cities = {c.code: c.state_id.name for c in proxy.city_ids}
            towns = {t.code: t.town_id.name for t in proxy.town_ids}

            def bank(b):
                if b:
                    c = banks.get(b, '-')
                    return '%s (%s)' % (c, b)
                return b

            def status(s):
                if s:
                    c = statuses.get(s, '-')
                    return '%s (%s)' % (c, s)
                return s

            def city(s):
                if s:
                    c = cities.get(s, '-')
                    return '%s (%s)' % (c, s)
                return s

            def town(t):
                if t:
                    c = towns.get(t, '-')
                    return '%s (%s)' % (c, t)
                return t

            params = self.env.context.get('params', {})
            values = {
                'name': 'Worldline',
                'code': 'worldline', 
                #'username': params.get('username', False),
                #'password': params.get('password', False),
                'talepNo': params.get('talepNo', False),
                'bildirenBankaKodu': bank(params.get('bildirenBankaKodu', False)),
                'bankaTalepNo': params.get('bankaTalepNo', False),
                'talepTipi': params.get('talepTipi', False),
                'cagriArizaSebebi': status(params.get('cagriArizaSebebi', False)),
                'musteriUiyNo': params.get('musteriUiyNo', False),
                'musteriUiyTerminalNo': params.get('musteriUiyTerminalNo', False),
                'uiyNo': params.get('uiyNo', False),
                'uiyTerminalNo': params.get('uiyTerminalNo', False),
                'mukellefUiyUnvaniAdi': params.get('mukellefUiyUnvaniAdi', False),
                'mukellefUiyAdresi': params.get('mukellefUiyAdresi', False),
                'mukellefUiyIlcesi': town(params.get('mukellefUiyIlcesi', False)),
                'mukellefUiyIli': city(params.get('mukellefUiyIli', False)),
                'mukellefUiyYetkiliAd': params.get('mukellefUiyYetkiliAd', False),
                'mukellefUiyYetkiliSoyad': params.get('mukellefUiyYetkiliSoyad', False),
                'mukellefUiyYetkiliUnvani': params.get('mukellefUiyYetkiliUnvani', False),
                'mukellefUiyVergiDairesi': params.get('mukellefUiyVergiDairesi', False),
                'mukellefUiyVergiNo': params.get('mukellefUiyVergiNo', False),
                'mukellefUiyTel1': params.get('mukellefUiyTel1', False),
                'mukellefUiyTel2': params.get('mukellefUiyTel2', False),
                'mukellefUiyGsmTel': params.get('mukellefUiyGsmTel', False),
                'mukellefUiyEmail': params.get('mukellefUiyEmail', False),
                'mukellefUiyMersisNo': params.get('mukellefUiyMersisNo', False),
                'mukellefUiyTicaretSicilNo': params.get('mukellefUiyTicaretSicilNo', False),
                'mukellefUiyEsnafSicilNo': params.get('mukellefUiyEsnafSicilNo', False),
                'altMusteriYeriFarkli': params.get('altMusteriYeriFarkli', False),
                'altMusteriUiyUnvaniAdi': params.get('altMusteriUiyUnvaniAdi', False),
                'altMusteriUiyAdresi': params.get('altMusteriUiyAdresi', False),
                'altMusteriUiyIlcesi': town(params.get('altMusteriUiyIlcesi', False)),
                'altMusteriUiyIli': city(params.get('altMusteriUiyIli', False)),
                'altMusteriUiyYetkiliAd': params.get('altMusteriUiyYetkiliAd', False),
                'altMusteriUiyYetkiliSoyad': params.get('altMusteriUiyYetkiliSoyad', False),
                'altMusteriUiyYetkiliUnvani': params.get('altMusteriUiyYetkiliUnvani', False),
                'altMusteriUiyVergiDairesi': params.get('altMusteriUiyVergiDairesi', False),
                'altMusteriUiyVergiNo': params.get('altMusteriUiyVergiNo', False),
                'altMusteriUiyTel1': params.get('altMusteriUiyTel1', False),
                'altMusteriUiyTel2': params.get('altMusteriUiyTel2', False),
                'altMusteriUiyGsmTel': params.get('altMusteriUiyGsmTel', False),
                'altMusteriUiyEmail': params.get('altMusteriUiyEmail', False),
                'altMusteriUiyMersisNo': params.get('altMusteriUiyMersisNo', False),
                'altMusteriUiyTicaretSicilNo': params.get('altMusteriUiyTicaretSicilNo', False),
                'altMusteriUiyEsnafSicilNo': params.get('altMusteriUiyEsnafSicilNo', False),
                'hizmetYeriFarkli': params.get('hizmetYeriFarkli', False),
                'hizmetYeriUiyUnvaniAdi': params.get('hizmetYeriUiyUnvaniAdi', False),
                'hizmetYeriUiyAdresi': params.get('hizmetYeriUiyAdresi', False),
                'hizmetYeriUiyIlcesi': town(params.get('hizmetYeriUiyIlcesi', False)),
                'hizmetYeriUiyIli': city(params.get('hizmetYeriUiyIli', False)),
                'hizmetYeriUiyYetkiliAd': params.get('hizmetYeriUiyYetkiliAd', False),
                'hizmetYeriUiyYetkiliSoyad': params.get('hizmetYeriUiyYetkiliSoyad', False),
                'hizmetYeriUiyYetkiliUnvani': params.get('hizmetYeriUiyYetkiliUnvani', False),
                'hizmetYeriUiyVergiDairesi': params.get('hizmetYeriUiyVergiDairesi', False),
                'hizmetYeriUiyVergiNo': params.get('hizmetYeriUiyVergiNo', False),
                'hizmetYeriUiyTel1': params.get('hizmetYeriUiyTel1', False),
                'hizmetYeriUiyTel2': params.get('hizmetYeriUiyTel2', False),
                'hizmetYeriUiyGsmTel': params.get('hizmetYeriUiyGsmTel', False),
                'hizmetYeriUiyEmail': params.get('hizmetYeriUiyEmail', False),
                'hizmetYeriUiyMersisNo': params.get('hizmetYeriUiyMersisNo', False),
                'hizmetYeriUiyTicaretSicilNo': params.get('hizmetYeriUiyTicaretSicilNo', False),
                'hizmetYeriUiyEsnafSicilNo': params.get('hizmetYeriUiyEsnafSicilNo', False),
                'cagriAciklama': params.get('cagriAciklama', False),
                'musteriOnceligi': params.get('musteriOnceligi', False),
                'bankaSubeKodu': params.get('bankaSubeKodu', False),
                'sektor': params.get('sektor', False),
                'cihazModel': params.get('cihazModel', False),
                'cihazSeriNo': params.get('cihazSeriNo', False),
                'uygulamaVersiyonNo': params.get('uygulamaVersiyonNo', False),
                'talebiIletenKullanici': params.get('talebiIletenKullanici', False),
                'projeAdi': params.get('projeAdi', False),
                'garantiKapsaminda': params.get('garantiKapsaminda', False),
                'yeniUyeNo': params.get('yeniUyeNo', False),
                'yeniTermNo': params.get('yeniTermNo', False),
                'yeniFirmaAdi': params.get('yeniFirmaAdi', False),
                'channelinfo': params.get('channelinfo', False),
                'stockstate': params.get('stockstate', False),
                'billingstate': params.get('billingstate', False),
                'cargodate': params.get('cargodate', False),
                'sicilno': params.get('sicilno', False),
                'izinYazisiTarihi': params.get('izinYazisiTarihi', False),
                'bankaSiparisNo': params.get('bankaSiparisNo', False),
                'RFU1': params.get('RFU1', False),
                'RFU2': params.get('RFU2', False),
                'RFU3': params.get('RFU3', False),
                'RFU4': params.get('RFU4', False),
                'RFU5': params.get('RFU5', False),
                'projeBaslangicTarihi': params.get('projeBaslangicTarihi', False),
                'projeGunSayisi': params.get('projeGunSayisi', False),
                'aksesuar': params.get('aksesuar', False)
            }

            log = self.env['fsm.api.log.worldline'].sudo().create(values)
            for task in self:
                task.api_log_worldline_id = log.id
