import json
import urllib.request

from odoo import models, fields, api
from odoo.exceptions import UserError


class CvParserProviderModel(models.Model):
    _name = 'cv.parser.provider.model'
    _description = 'AI Sağlayıcı Model'
    _order = 'name'

    provider_id = fields.Many2one('cv.parser.provider', ondelete='cascade', required=True)
    model_id = fields.Char(string='Model ID', required=True)
    name = fields.Char(string='Model Adı')

    def name_get(self):
        return [(r.id, r.name or r.model_id) for r in self]


class CvParserProvider(models.Model):
    _name = 'cv.parser.provider'
    _description = 'CV Parser AI Sağlayıcı'
    _order = 'sequence, name'

    name = fields.Char(string='Sağlayıcı Adı', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    status = fields.Selection([
        ('draft', 'Test Edilmedi'),
        ('confirmed', 'Onaylandı'),
        ('error', 'Hata'),
    ], string='Durum', default='draft', readonly=True)
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://openrouter.ai/api/v1/chat/completions',
    )
    balance_url = fields.Char(
        string='Bakiye URL',
        default='https://openrouter.ai/api/v1/auth/key',
    )
    models_url = fields.Char(
        string='Modeller URL',
        default='https://openrouter.ai/api/v1/models',
    )
    api_key = fields.Char(string='API Key', required=True)
    notes = fields.Text(string='Notlar')
    model_ids = fields.One2many('cv.parser.provider.model', 'provider_id', string='Modeller')
    model_count = fields.Integer(compute='_compute_model_count', string='Model Sayısı')

    @api.depends('model_ids')
    def _compute_model_count(self):
        for rec in self:
            rec.model_count = len(rec.model_ids)

    def action_test_connection(self):
        self.ensure_one()
        try:
            req = urllib.request.Request(
                self.balance_url or self.api_url,
                headers={'Authorization': 'Bearer ' + self.api_key},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            self.status = 'confirmed'
        except Exception as e:
            self.status = 'error'
            raise UserError("Bağlantı başarısız: " + str(e))

        self._fetch_models()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bağlantı Başarılı',
                'message': '%d model yüklendi.' % len(self.model_ids),
                'type': 'success',
                'sticky': False,
            }
        }

    def _fetch_models(self):
        self.ensure_one()
        if not self.models_url:
            return
        try:
            req = urllib.request.Request(
                self.models_url,
                headers={'Authorization': 'Bearer ' + self.api_key},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception:
            return

        models_data = data.get('data', [])
        if not models_data:
            return

        self.model_ids.unlink()
        vals = []
        for m in models_data:
            model_id = m.get('id', '')
            name = m.get('name') or model_id
            if model_id:
                vals.append({
                    'provider_id': self.id,
                    'model_id': model_id,
                    'name': name,
                })
        if vals:
            self.env['cv.parser.provider.model'].create(vals)

    def action_check_balance(self):
        self.ensure_one()
        if not self.balance_url:
            raise UserError("Bu sağlayıcı için bakiye URL tanımlanmamış.")

        req = urllib.request.Request(
            self.balance_url,
            headers={'Authorization': 'Bearer ' + self.api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8')).get('data', {})
        except Exception as e:
            raise UserError("Bakiye sorgulanamadı: " + str(e))

        limit = data.get('limit')
        usage = data.get('usage', 0)
        remaining = (limit - usage) if limit else None

        lines = ["Sağlayıcı: " + self.name]
        if limit:
            lines.append("Toplam Limit: $%.4f" % limit)
        lines.append("Kullanılan: $%.4f" % usage)
        if remaining is not None:
            lines.append("Kalan: $%.4f" % remaining)
        if data.get('is_free_tier'):
            lines.append("(Ücretsiz plan)")

        raise UserError("\n".join(lines))
