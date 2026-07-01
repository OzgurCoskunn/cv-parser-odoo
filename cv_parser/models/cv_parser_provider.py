import json
import urllib.request

from odoo import models, fields
from odoo.exceptions import UserError


class CvParserProvider(models.Model):
    _name = 'cv.parser.provider'
    _description = 'CV Parser AI Sağlayıcı'
    _order = 'sequence, name'

    name = fields.Char(string='Sağlayıcı Adı', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://openrouter.ai/api/v1/chat/completions',
    )
    balance_url = fields.Char(
        string='Bakiye URL',
        default='https://openrouter.ai/api/v1/auth/key',
    )
    api_key = fields.Char(string='API Key', required=True)
    notes = fields.Text(string='Notlar')

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
