from odoo import models, fields, api


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'
    _rec_name = 'description'

    product_id = fields.Many2one('product.product', required=True, string="Product")
    description = fields.Char(related='product_id.product_tmpl_id.name', string='Description')
    quantity = fields.Float(string="Quantity", default=1.0)
    cost_price = fields.Float(readonly=True, related='product_id.standard_price')
    total = fields.Float(readonly=True, compute='_compute_total', string='Total')
    purchase_request_id = fields.Many2one('purchase.request', string='Purchase Request')

    @api.depends('quantity', 'cost_price')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.quantity * rec.cost_price
