# -*- coding: utf-8 -*-
from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import request, route, Controller, STATIC_CACHE_LONG
from odoo.exceptions import AccessError, UserError
from odoo.tools import replace_exceptions
from odoo.addons.mail.controllers import discuss


class FsmController(Controller):

    @route('/fsm/access/chatter', methods=['POST'], type='jsonrpc', auth='user')
    def access_chatter(self, model, id, **kwargs):
        #record = request.env[model].with_context(active_test=False).search([('id', '=', id)])
        has_manager_access = request.env.user.has_group('fsm.group_manager')
        if not has_manager_access:
            has_message_access = request.env.user.has_group('fsm.group_chatter_message')
            has_note_access = request.env.user.has_group('fsm.group_chatter_note')
            has_activity_access = request.env.user.has_group('fsm.group_chatter_activity')
            has_attachment_access = request.env.user.has_group('fsm.group_chatter_attachment')
            has_follower_access = request.env.user.has_group('fsm.group_chatter_follower')
            has_log_access = request.env.user.has_group('fsm.group_chatter_log')
        else:
            has_message_access = True
            has_note_access = True
            has_activity_access = True
            has_attachment_access = True
            has_follower_access = True
            has_log_access = True

        return {
            'hasMessageAccess': has_message_access,
            'hasNoteAccess': has_note_access,
            'hasActivityAccess': has_activity_access,
            'hasAttachmentAccess': has_attachment_access,
            'hasFollowerAccess': has_follower_access,
            'hasLogAccess': has_log_access,
        }


    @route('/fsm/<uid>/document/<token>', methods=['GET'], type='http', auth='public')
    def access_document(self, uid, token, **kwargs):
        task = request.env['fsm.task'].sudo().search([
            ('uid', '=', uid),
        ], limit=1)
        if not task:
            raise NotFound()

        attachment = request.env['ir.attachment'].sudo().search([
            ('access_token', '=', token),
        ], limit=1)
        if not attachment:
            raise NotFound()

        with replace_exceptions(UserError, by=request.not_found()):
            stream = request.env['ir.binary']._get_stream_from(attachment, 'raw', None, 'name', None)
            if request.httprequest.args.get('access_token'):
                stream.public = True

        send_file_kwargs = {
            'as_attachment': False,
            'immutable': True,
            'max_age': STATIC_CACHE_LONG,
        }

        return stream.get_response(**send_file_kwargs)


from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store


class FsmThreadController(ThreadController):

    @route('/mail/thread/messages', methods=['POST'], type='jsonrpc', auth='user')
    def mail_thread_messages(self, thread_model, thread_id, fetch_params=None):
        if thread_model == 'fsm.task':
            thread = self._get_thread_with_access(thread_model, thread_id, mode="read")
            res = request.env["mail.message"]._message_fetch(domain=None, thread=thread, **(fetch_params or {}))
            messages = res.pop("messages")

            task = request.env[thread_model].browse(int(thread_id))
            additional_res = request.env['mail.message']._message_fetch(domain=[
                ('res_id', 'in', task.product_ids.ids),
                ('model', '=', thread_model + '.product'),
                ('message_type', '!=', 'user_notification'),
            ], **(fetch_params or {}))
            messages |= additional_res['messages']
            
            # Sort messages to ensure correct order after merge (assuming ID sort is sufficient/default)
            messages = messages.sorted(key=lambda m: m.id, reverse=True)

            if not request.env.user._is_public():
                messages.set_message_done()
            
            store = Store().add(messages)
            data = store.get_result()
            
            # Patch data to make product messages appear as task messages
            if 'Mail.Message' in data:
                 for msg_data in data['Mail.Message'].values():
                      if msg_data.get('model') == thread_model + '.product':
                           msg_data['model'] = thread_model
                           msg_data['res_id'] = int(thread_id)

            return {
                **res,
                "data": data,
                "messages": messages.ids,
            }
        return super().mail_thread_messages(thread_model, thread_id, fetch_params=fetch_params)
