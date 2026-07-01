import json
import re
import urllib.request

from odoo import models, fields
from odoo.exceptions import UserError


SUPPORTED_MIMES = (
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    x_cv_parsed = fields.Boolean(string='CV Bilgisi Alındı', default=False)

    def action_parse_cv_with_llm(self):
        self.ensure_one()

        if self.x_cv_parsed:
            raise UserError(
                "Bu aday için CV bilgisi daha önce alındı.\n"
                "Tekrar çekmek için 'CV Bilgisi Alındı' işaretini kaldırın."
            )

        cv_attachment = self._find_cv_attachment()
        if not cv_attachment:
            raise UserError("CV eki bulunamadı. Lütfen PDF veya Word formatında CV ekleyin.")

        configs = self.env['cv.parser.config'].get_active_configs()
        last_error = None

        for config in configs:
            # limit kontrolü
            if config.check_spend_limit():
                last_error = "Harcama limiti aşıldı, konfigürasyon pasife alındı: %s" % config.name
                continue

            provider = config.provider_id
            try:
                cv_data, usage, req_payload, resp_payload = self._call_provider(
                    provider, config.llm_model, config.prompt, cv_attachment
                )
            except Exception as e:
                last_error = str(e)
                self._log_error_independent(
                    res_name=self.partner_name or str(self.id),
                    llm_model=config.llm_model,
                    error_message=str(e),
                    provider_id=provider.id,
                    config_id=config.id,
                )
                config.write({
                    'active': False,
                    'deactivation_reason': 'API hatası: ' + str(e)[:200],
                })
                continue

            # başarılı
            vals = self._extract_vals(cv_data)
            vals['x_cv_parsed'] = True
            self.write(vals)

            self.env['openrouter.log'].sudo()._create_log(
                res_model='hr.applicant',
                res_id=self.id,
                res_name=cv_data.get('partner_name') or self.partner_name or str(self.id),
                llm_model=config.llm_model,
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
                status='success',
                request_payload=req_payload,
                response_payload=resp_payload,
                provider_id=provider.id,
                config_id=config.id,
            )
            return

        raise UserError(
            "Tüm konfigürasyonlar başarısız oldu veya pasife alındı.\n"
            "Son hata: " + (last_error or 'Bilinmiyor')
        )

    def _log_error_independent(self, res_name, llm_model, error_message, provider_id, config_id):
        # Ayrı cursor: dış transaction rollback olsa bile log kalır
        try:
            registry = self.env.registry
            with registry.cursor() as cr:
                env = self.env(cr=cr)
                env['openrouter.log'].sudo()._create_log(
                    res_model='hr.applicant',
                    res_id=self.id,
                    res_name=res_name,
                    llm_model=llm_model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    status='error',
                    error_message=error_message,
                    provider_id=provider_id,
                    config_id=config_id,
                )
        except Exception:
            pass

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

    def _call_provider(self, provider, llm_model, prompt, cv_attachment):
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
                {'type': 'text', 'text': prompt},
                file_content,
            ]
        }]

        payload = json.dumps({
            'model': llm_model,
            'messages': messages,
            'temperature': 0,
        }).encode('utf-8')

        req = urllib.request.Request(
            provider.api_url,
            data=payload,
            headers={
                'Authorization': 'Bearer ' + provider.api_key,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://odoo.internal',
                'X-Title': 'Odoo CV Parser',
            }
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        raw_content = result['choices'][0]['message']['content']
        usage = result.get('usage', {})
        req_payload = json.dumps({'model': llm_model, 'prompt': prompt}, ensure_ascii=False)

        try:
            cv_data = json.loads(raw_content)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if m:
                cv_data = json.loads(m.group())
            else:
                raise UserError("LLM yanıtı JSON olarak okunamadı:\n" + raw_content)

        return cv_data, usage, req_payload, raw_content

    def _extract_vals(self, cv_data):
        vals = {}
        if cv_data.get('partner_name') and not self.partner_name:
            vals['partner_name'] = cv_data['partner_name']
        if cv_data.get('partner_phone') and not self.partner_phone:
            vals['partner_phone'] = cv_data['partner_phone']
        if cv_data.get('email_from') and not self.email_from:
            vals['email_from'] = cv_data['email_from']
        if cv_data.get('linkedin') and not self.linkedin_profile:
            vals['linkedin_profile'] = cv_data['linkedin']
        return vals
