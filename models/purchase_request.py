from odoo import models, fields, api, _, exceptions


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Request Name", required=True)
    sequence = fields.Char(string='Sequence', required=True, copy=False, default="New")
    requested_by = fields.Many2one('res.users', string="Requested by", required=True,
                                   default=lambda self: self.env.user)
    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To Be Approved'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('cancel', 'Cancel')],
        default='draft')
    reject_reasons_ids = fields.One2many('rejection.reason', 'purchase_request_id', string="Rejection Reason",
                                         readonly=True)
    total_price = fields.Float(readonly=True, compute='_compute_total_sum', string='Total')
    order_lines_ids = fields.One2many('purchase.request.line', 'purchase_request_id', string="Order Lines")
    purchase_order_ids = fields.One2many('purchase.order', 'purchase_request_id', string="Purchase Order")

    def create_po(self):
        # Create new Purchase Order record
        for rec in self:
            for line in rec.order_lines_ids:
                vendor_id = self.requested_by.id
                purchase_order = rec.env['purchase.order'].create({
                    'name': rec.sequence,
                    'partner_id': vendor_id,
                    'date_approve': rec.start_date,
                    'user_id': rec.requested_by.id,
                    'amount_total': rec.total_price,
                    'date_planned': rec.end_date,
                })
                self.env['purchase.order.line'].create({
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'price_unit': line.product_id.standard_price,
                })
            # rec.purchase_order_id = purchase_order.id

        # Link the PR to the new PO
        # self.write({
        #     'purchase_order_ids': [(4, purchase_order.id)]
        # })

        # Return action to open the new PO record
        # action = self.env.ref('purchase.purchase_form_action')
        # result = action.read()[0]
        # result['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
        # result['res_id'] = purchase_order.id
        # return result

    def write(self, vals):
        res = super(PurchaseRequest, self).write(vals)
        for rec in self:
            if rec.state == "reject" and rec.reject_reasons_ids.reject_reason != False:
                message = "Rejection reason is: %s" % rec.reject_reasons_ids.reject_reason
                rec.message_post(body=message)
        return res

    @api.model
    def create(self, vals):
        if vals.get('sequence', _("New")) == _("New"):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('purchase_request.sequence') or _("New")
        res = super(PurchaseRequest, self).create(vals)
        return res

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError('Deletion is only possible for records in draft state.')
        return super(PurchaseRequest, self).unlink()

    @api.depends('order_lines_ids.total')
    def _compute_total_sum(self):
        for rec in self:
            rec.total_price = sum(line.total for line in rec.order_lines_ids)

    def submit_for_approval(self):
        self.state = 'to_be_approved'

    def cancel(self):
        self.state = 'cancel'

    def approve(self):
        self.state = 'approve'
        template = self.env.ref('purchase_request.email_template_approve_purchase_request')
        for rec in self:
            template.send_mail(rec.id, force_send=True)

    def reject(self):
        self.state = 'reject'
        action = self.env.ref('purchase_request.reject_request_action').read()[0]
        return action

    def reset_to_draft(self):
        self.state = 'draft'


class RejectionReason(models.Model):
    _name = 'rejection.reason'
    _description = 'Rejection Reason'

    reject_reason = fields.Text(string="Rejection Reason")
    reject_user = fields.Many2one('res.users', string="Rejected by", required=True,
                                  default=lambda self: self.env.user, readonly=True)
    purchase_request_id = fields.Many2one('purchase.request', string="Purchase Request")


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one('purchase.request', string="Purchase Request")
