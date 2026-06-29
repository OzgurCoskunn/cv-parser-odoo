import json
import urllib.request

from odoo import models, fields, api
from odoo.exceptions import UserError


class OpenRouterLog(models.Model):
    _name = 'openrouter.log'
    _description = 'OpenRouter Kullanım Kaydı'
    _order = 'date desc'

    date = fields.Datetime(string='Tarih', default=fields.Datetime.now, readonly=True)
    res_model = fields.Char(string='Model', readonly=True)
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

    # Özet istatistikler (read-only hesaplanan alanlar)
    total_requests = fields.Integer(
        string='Toplam İstek',
        compute='_compute_stats',
    )
    total_cost = fields.Float(
        string='Toplam Maliyet (USD)',
        digits=(10, 4),
        compute='_compute_stats',
    )
    avg_cost = fields.Float(
        string='Ortalama Maliyet (USD)',
        digits=(10, 6),
        compute='_compute_stats',
    )

    @api.depends()
    def _compute_stats(self):
        all_logs = self.search([('status', '=', 'success')])
        total = len(all_logs)
        total_cost = sum(all_logs.mapped('cost_usd'))
        avg = total_cost / total if total else 0.0
        for rec in self:
            rec.total_requests = total
            rec.total_cost = total_cost
            rec.avg_cost = avg

    @api.model
    def action_check_balance(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('openrouter.api_key')
        if not api_key:
            raise UserError("OpenRouter API key bulunamadı. Sistem Parametreleri > 'openrouter.api_key'")

        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/auth/key',
            headers={'Authorization': 'Bearer ' + api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8')).get('data', {})
        except Exception as e:
            raise UserError("Bakiye sorgulanamadı: " + str(e))

        limit = data.get('limit')
        usage = data.get('usage', 0)
        remaining = (limit - usage) if limit else None

        lines = []
        if limit:
            lines.append("Toplam Limit: $%.4f" % limit)
        lines.append("Kullanılan: $%.4f" % usage)
        if remaining is not None:
            lines.append("Kalan: $%.4f" % remaining)
        if data.get('is_free_tier'):
            lines.append("(Ücretsiz plan)")

        raise UserError("OpenRouter Bakiye\n\n" + "\n".join(lines))

    @api.model
    def _create_log(self, res_model, res_id, res_name, llm_model,
                    prompt_tokens, completion_tokens, status='success', error_message=None,
                    request_payload=None, response_payload=None):
        MODEL_PRICES = {
            'anthropic/claude-haiku-4.5': (1.0, 5.0),
            'anthropic/claude-sonnet-4.5': (3.0, 15.0),
            'anthropic/claude-sonnet-4.6': (3.0, 15.0),
            'anthropic/claude-opus-4.6': (15.0, 75.0),
        }
        input_price, output_price = MODEL_PRICES.get(llm_model, (3.0, 15.0))
        cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000

        self.create({
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
