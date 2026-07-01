from odoo import models, fields, api
from odoo.exceptions import UserError


class CvParserLog(models.Model):
    _name = 'cv.parser.log'
    _description = 'CV Parser Log'
    _order = 'date desc'

    date = fields.Datetime(string='Tarih', default=fields.Datetime.now, readonly=True)
    provider_id = fields.Many2one('cv.parser.provider', string='Sağlayıcı', readonly=True)
    config_id = fields.Many2one('cv.parser.config', string='Konfigürasyon', readonly=True, ondelete='set null')
    res_model = fields.Char(string='İlgili Model', readonly=True)
    res_id = fields.Integer(string='Kayıt ID', readonly=True)
    res_name = fields.Char(string='Kayıt Adı', readonly=True)
    llm_model = fields.Char(string='LLM Model', readonly=True)
    prompt_tokens = fields.Integer(string='Prompt Token', readonly=True)
    completion_tokens = fields.Integer(string='Tamamlama Token', readonly=True)
    total_tokens = fields.Integer(string='Toplam Token', readonly=True)
    cost_usd = fields.Float(string='Tahmini Maliyet (USD)', digits=(10, 6), readonly=True)
    status = fields.Selection([
        ('success', 'Başarılı'),
        ('error', 'Hata'),
    ], string='Durum', default='success', readonly=True)
    error_message = fields.Text(string='Hata Mesajı', readonly=True)
    request_payload = fields.Text(string='Gönderilen İstek', readonly=True)
    response_payload = fields.Text(string='Dönen Yanıt', readonly=True)

    @api.model
    def action_check_balance(self):
        providers = self.env['cv.parser.provider'].search([('active', '=', True)])
        if not providers:
            raise UserError("Aktif sağlayıcı bulunamadı. CV Parser Ayarları > AI Sağlayıcılar")
        return providers[0].action_check_balance()

    @api.model
    def _create_log(self, res_model, res_id, res_name, llm_model,
                    prompt_tokens, completion_tokens, status='success', error_message=None,
                    request_payload=None, response_payload=None, provider_id=None, config_id=None):
        MODEL_PRICES = {
            'anthropic/claude-haiku-4.5': (1.0, 5.0),
            'anthropic/claude-sonnet-4.5': (3.0, 15.0),
            'anthropic/claude-sonnet-4.6': (3.0, 15.0),
            'anthropic/claude-opus-4.6': (15.0, 75.0),
        }
        input_price, output_price = MODEL_PRICES.get(llm_model, (3.0, 15.0))
        cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000

        self.create({
            'provider_id': provider_id,
            'config_id': config_id,
            'res_model': res_model,
            'res_id': res_id,
            'res_name': res_name,
            'llm_model': llm_model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'cost_usd': cost,
            'status': status,
            'error_message': error_message,
            'request_payload': request_payload,
            'response_payload': response_payload,
        })
