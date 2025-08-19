from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InterventionProductLine(models.Model):
    _name = 'intervention.product.line'
    _description = 'Pièce utilisée lors d\'une intervention'

    ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Ticket',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
        domain=[('type', '!=', 'service')]
    )
    
    quantity = fields.Float(
        'Quantité',
        default=1.0,
        required=True
    )
    
    unit_price = fields.Float(
        'Prix unitaire',
        related='product_id.list_price',
        readonly=True
    )
    
    subtotal = fields.Float(
        'Sous-total',
        compute='_compute_subtotal',
        store=True
    )
    
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Mouvement de stock',
        readonly=True
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.model
    def create(self, vals):
        """Création avec vérification de stock"""
        line = super().create(vals)
        line._check_and_reserve_stock()
        return line

    def write(self, vals):
        """Mise à jour avec gestion du stock"""
        result = super().write(vals)
        if 'quantity' in vals or 'product_id' in vals:
            for line in self:
                line._check_and_reserve_stock()
        return result

    def _check_and_reserve_stock(self):
        """Vérification et réservation du stock"""
        if not self.product_id:
            return
        
        # Vérifier la disponibilité en stock
        available_qty = self.product_id.qty_available
        if available_qty < self.quantity:
            raise UserError(
                _("Stock insuffisant pour %s.\nDisponible: %s, Demandé: %s") % (
                    self.product_id.name,
                    available_qty,
                    self.quantity
                )
            )
        
        # Créer le mouvement de stock si pas déjà fait
        if not self.stock_move_id:
            self._create_stock_move()

    def _create_stock_move(self):
        """Création du mouvement de stock"""
        # Localisation source (stock)
        source_location = self.env.ref('stock.stock_location_stock')
        # Localisation de destination (client/intervention)
        dest_location = self.env.ref('stock.stock_location_customers')
        
        move_vals = {
            'name': f'Intervention: {self.product_id.name}',
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.ticket_id.name,
        }
        
        stock_move = self.env['stock.move'].create(move_vals)
        stock_move._action_confirm()
        stock_move._action_done()
        
        self.stock_move_id = stock_move.id

    def unlink(self):
        """Suppression avec annulation du mouvement de stock"""
        for line in self:
            if line.stock_move_id and line.stock_move_id.state == 'done':
                # Créer un mouvement de retour
                return_move = line.stock_move_id.copy({
                    'location_id': line.stock_move_id.location_dest_id.id,
                    'location_dest_id': line.stock_move_id.location_id.id,
                    'origin': f'Retour {line.stock_move_id.origin}',
                })
                return_move._action_confirm()
                return_move._action_done()
        
        return super().unlink()