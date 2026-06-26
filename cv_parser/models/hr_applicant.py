import base64
import json
import re
import urllib.request

from odoo import models
from odoo.exceptions import UserError


SUPPORTED_MIMES = (
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
)

LLM_MODEL = 'anthropic/claude-sonnet-4.5'

PROMPT = """Bu CV'yi analiz et. Yalnızca aşağıdaki JSON formatında döndür, başka hiçbir şey yazma:
{
  "partner_name":   "Ad Soyad",
  "partner_phone":  "Telefon numarası (varsa, yoksa boş string)",
  "email_from":     "E-posta adresi (varsa, yoksa boş string)",
  "linkedin":       "LinkedIn URL (varsa, yoksa boş string)"
}"""


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def action_parse_cv_with_llm(self):
        self.ensure_one()

        api_key = self.env['ir.config_parameter'].sudo().get_param('openrouter.api_key')
        if not api_key:
            raise UserError("OpenRouter API key bulunamadı.\nAyarlar > Teknik > Sistem Parametreleri > 'openrouter.api_key'")

        cv_attachment = self._find_cv_attachment()
        if not cv_attachment:
            raise UserError("CV eki bulunamadı. Lütfen PDF veya Word formatında CV ekleyin.")

        try:
            cv_data, usage = self._call_openrouter(api_key, cv_attachment)
        except UserError:
            raise
        except Exception as e:
            self.env['openrouter.log'].sudo()._create_log(
                res_model='hr.applicant',
                res_id=self.id,
                res_name=self.partner_name or str(self.id),
                llm_model=LLM_MODEL,
                prompt_tokens=0,
                completion_tokens=0,
                status='error',
                error_message=str(e),
            )
            raise UserError("OpenRouter API hatası: " + str(e))

        vals = self._extract_vals(cv_data)
        if vals:
            self.write(vals)

        self.env['openrouter.log'].sudo()._create_log(
            res_model='hr.applicant',
            res_id=self.id,
            res_name=cv_data.get('partner_name') or self.partner_name or str(self.id),
            llm_model=LLM_MODEL,
            prompt_tokens=usage.get('prompt_tokens', 0),
            completion_tokens=usage.get('completion_tokens', 0),
            status='success',
        )

        updated = ', '.join(vals.keys()) if vals else 'Yeni bilgi bulunamadı'
        raise UserError("CV başarıyla okundu!\n\nGüncellenen alanlar: " + updated)

    def _find_cv_attachment(self):
        attachment = self.message_main_attachment_id
        if attachment and attachment.mimetype in SUPPORTED_MIMES:
            return attachment

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', list(SUPPORTED_MIMES)),
            '|', ('name', 'ilike', 'cv'), ('name', 'ilike', 'resume'),
        ], limit=1)
        if attachment:
            return attachment

        return self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', list(SUPPORTED_MIMES)),
        ], order='id asc', limit=1)

    def _call_openrouter(self, api_key, cv_attachment):
        b64 = cv_attachment.datas.decode('utf-8')
        mime = cv_attachment.mimetype

        if 'pdf' in mime:
            file_content = {
                'type': 'file',
                'file': {
                    'filename': cv_attachment.name or 'cv.pdf',
                    'file_data': 'data:' + mime + ';base64,' + b64,
                }
            }
        else:
            file_content = {
                'type': 'image_url',
                'image_url': {'url': 'data:' + mime + ';base64,' + b64}
            }

        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': PROMPT},
                file_content,
            ]
        }]

        payload = json.dumps({
            'model': LLM_MODEL,
            'messages': messages,
            'temperature': 0,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=payload,
            headers={
                'Authorization': 'Bearer ' + api_key,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://odoo.internal',
                'X-Title': 'Odoo CV Parser',
            }
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        raw_content = result['choices'][0]['message']['content']
        usage = result.get('usage', {})

        try:
            cv_data = json.loads(raw_content)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if m:
                cv_data = json.loads(m.group())
            else:
                raise UserError("LLM yanıtı JSON olarak okunamadı:\n" + raw_content)

        return cv_data, usage

    def _extract_vals(self, cv_data):
        vals = {}
        if cv_data.get('partner_name') and not self.partner_name:
            vals['partner_name'] = cv_data['partner_name']
        if cv_data.get('partner_phone') and not self.partner_phone:
            vals['partner_phone'] = cv_data['partner_phone']
        if cv_data.get('email_from') and not self.email_from:
            vals['email_from'] = cv_data['email_from']
        return vals
