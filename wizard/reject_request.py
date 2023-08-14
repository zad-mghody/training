from odoo import models, fields, api


class RejectRequestWizard(models.TransientModel):
    _name = "reject.request.wizard"
    _description = "Reject Request Wizard"

    purchase_request_id = fields.Many2one('purchase.request', string="Request Name", readonly=True)
    reject_reason = fields.Text(string="Rejection Reason", store=True)
    reject_user = fields.Many2one('res.users', string="Rejected by", required=True,
                                  default=lambda self: self.env.user, readonly=True)

    def default_get(self, fields):
        result = super(RejectRequestWizard, self).default_get(fields)
        result['purchase_request_id'] = self.env.context.get('active_id')
        return result

    def save_action(self):
        self.purchase_request_id.state = 'reject'
        line_values = []
        for line in self:
            line_values.append((0, 0, {
                'reject_reason': line.reject_reason,
                'reject_user': line.reject_user.id,
            }))
        self.purchase_request_id.reject_reasons_ids = line_values

    def cancel_action(self):
        self.purchase_request_id.state = 'to_be_approved'
