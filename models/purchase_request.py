from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Request Name", required=True)
    sequence = fields.Char(string='Sequence', required=True, copy=False, default="New")
    requested_by = fields.Many2one('res.users', string="Requested by", required=True,
                                   default=lambda self: self.env.user)
    # default = lambda self: self.env.user.partner_id.id
    vendor_id = fields.Many2one('res.partner', )
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
    po_active = fields.Boolean(compute="_check_po_button", default=True, readonly=False)
    orders_count = fields.Integer(string="Orders Count", compute='_compute_order_count', default=0)

    # purchase_order_line_ids = fields.One2many('purchase.order.line', 'purchase_request_id', string="Purchase Order")

    def _compute_order_count(self):
        for rec in self:
            rec.orders_count = self.env['purchase.order'].search_count([('purchase_request_id', '=', rec.id)])

    def action_open_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('purchase_request_id', '=', self.id)],
            'target': 'current',

        }

    @api.depends('order_lines_ids.remaining_qty')
    def _check_po_button(self):
        for rec in self:
            rec.po_active = any([line.remaining_qty for line in rec.order_lines_ids])

    @api.depends('order_lines_ids.total')
    def _compute_total_sum(self):
        for rec in self:
            rec.total_price = sum(line.total for line in rec.order_lines_ids)

    def create_po(self):

        values = []
        lines_list = []
        for rec in self:
            for line in rec.order_lines_ids:
                lines_list.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.remaining_qty,
                    'max_qty': line.remaining_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'price_unit': line.product_id.standard_price,
                    'purchase_request_line_id': line.id,
                }))
            values.append((0, 0, {
                'partner_id': rec.vendor_id.id,
                'date_planned': rec.start_date,
                'amount_total': rec.total_price,
                'date_order': rec.end_date,
                'user_id': rec.requested_by.id,
                'order_line': lines_list,
            }))
        self.purchase_order_ids = values

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


class NewPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    purchase_request_line_id = fields.Many2one('purchase.request.line', string="Purchase Request")
    max_qty = fields.Float(readonly=True)

    @api.constrains('product_qty')
    def check_qty(self):
        for rec in self:
            print(rec.purchase_request_line_id.remaining_qty)
            print(rec.product_qty)
            if rec.product_qty > rec.purchase_request_line_id.remaining_qty + rec.product_qty:
                raise ValidationError(
                    f"Quantity of {rec.purchase_request_line_id.description} should not exceed the quantity {rec.purchase_request_line_id.remaining_qty + rec.product_qty}")
