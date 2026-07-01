from odoo import models, fields, api
from odoo.exceptions import UserError

DEFAULT_PROMPT = """Bu CV'yi analiz et. Yalnızca aşağıdaki JSON formatında döndür, başka hiçbir şey yazma:
{
  "partner_name":   "Ad Soyad",
  "partner_phone":  "Telefon numarası (varsa, yoksa boş string)",
  "email_from":     "E-posta adresi (varsa, yoksa boş string)",
  "linkedin":       "LinkedIn URL (varsa, yoksa boş string)"
}"""


class CvParserConfig(models.Model):
    _name = 'cv.parser.config'
    _description = 'CV Parser Konfigürasyon'

    name = fields.Char(string='Konfigürasyon Adı', required=True, default='Varsayılan')
    active = fields.Boolean(default=True)
    provider_id = fields.Many2one(
        'cv.parser.provider',
        string='AI Sağlayıcı',
        required=True,
        domain=[('active', '=', True)],
    )
    llm_model = fields.Char(
        string='Model',
        required=True,
        default='anthropic/claude-sonnet-4.5',
        help='Örn: anthropic/claude-sonnet-4.5',
    )
    prompt = fields.Text(string='Prompt', required=True, default=DEFAULT_PROMPT)
    max_spend_usd = fields.Float(
        string='Maksimum Harcama Limiti ($)',
        digits=(10, 2),
        default=0.0,
        help='0 = limit yok',
    )
    limit_action = fields.Selection([
        ('stop', 'Durdur'),
        ('warn', 'Uyar ve Devam Et'),
    ], string='Limit Aşılınca', default='stop')

    @api.model
    def get_active_config(self):
        config = self.search([('active', '=', True)], limit=1, order='id asc')
        if not config:
            raise UserError(
                "CV Parser konfigürasyonu bulunamadı.\n"
                "İşe Alım > Yapılandırma > CV Parser Ayarları"
            )
        return config

    def check_spend_limit(self):
        if not self.max_spend_usd:
            return
        total_spent = sum(
            self.env['openrouter.log'].search([
                ('provider_id', '=', self.provider_id.id),
                ('status', '=', 'success'),
            ]).mapped('cost_usd')
        )
        if total_spent >= self.max_spend_usd:
            if self.limit_action == 'stop':
                raise UserError(
                    "Maksimum harcama limitine ulaşıldı ($%.2f).\n"
                    "CV Parser Ayarları > Limit Aşılınca ayarını 'Uyar ve Devam Et' yapabilirsiniz."
                    % self.max_spend_usd
                )
