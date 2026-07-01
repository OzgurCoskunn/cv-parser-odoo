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
    _order = 'sequence, id'

    name = fields.Char(string='Konfigürasyon Adı', required=True)
    sequence = fields.Integer(string='Öncelik', default=10)
    active = fields.Boolean(default=True)
    provider_id = fields.Many2one(
        'cv.parser.provider',
        string='AI Sağlayıcı',
        required=True,
        domain=[('active', '=', True)],
    )
    provider_model_id = fields.Many2one(
        'cv.parser.provider.model',
        string='Model',
        domain="[('provider_id', '=', provider_id)]",
    )
    llm_model = fields.Char(
        string='Model ID',
        compute='_compute_llm_model',
        store=True,
    )
    prompt = fields.Text(string='Prompt', required=True, default=DEFAULT_PROMPT)
    max_spend_usd = fields.Float(
        string='Maksimum Harcama Limiti ($)',
        digits=(10, 2),
        default=0.0,
        help='0 = limit yok',
    )
    limit_action = fields.Selection([
        ('stop', 'Durdur ve Pasife Al'),
        ('warn', 'Uyar ve Devam Et'),
    ], string='Limit Aşılınca', default='stop')
    deactivation_reason = fields.Char(string='Pasife Alınma Nedeni', readonly=True)

    @api.depends('provider_model_id')
    def _compute_llm_model(self):
        for rec in self:
            rec.llm_model = rec.provider_model_id.model_id if rec.provider_model_id else ''

    @api.model
    def get_active_configs(self):
        configs = self.search([('active', '=', True)], order='sequence, id')
        if not configs:
            raise UserError(
                "Aktif CV Parser konfigürasyonu bulunamadı.\n"
                "İşe Alım > Yapılandırma > CV Parser Ayarları > Konfigürasyon"
            )
        return configs

    def check_spend_limit(self):
        self.ensure_one()
        if not self.max_spend_usd:
            return False
        total_spent = sum(
            self.env['openrouter.log'].search([
                ('provider_id', '=', self.provider_id.id),
                ('status', '=', 'success'),
            ]).mapped('cost_usd')
        )
        if total_spent >= self.max_spend_usd:
            if self.limit_action == 'stop':
                self.write({
                    'active': False,
                    'deactivation_reason': 'Harcama limiti aşıldı ($%.4f / $%.4f)' % (total_spent, self.max_spend_usd),
                })
                return True
        return False
