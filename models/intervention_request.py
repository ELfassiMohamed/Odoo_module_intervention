from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class InterventionCategory(models.Model):
    _name = 'intervention.category'
    _description = 'Catégorie d\'intervention'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur')

class InterventionRequest(models.Model):
    _name = 'intervention.request'
    _description = 'Demande d\'intervention'
    _order = 'priority desc, create_date desc'
    _rec_name = 'title'

    # Informations de base
    title = fields.Char(string='Titre', required=True)
    description = fields.Html(string='Description détaillée')
    
    # Client et contacts
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    contact_name = fields.Char(string='Nom du contact')
    contact_phone = fields.Char(string='Téléphone')
    contact_email = fields.Char(string='Email')
    
    # Catégorisation
    category_id = fields.Many2one('intervention.category', string='Catégorie', required=True)
    priority = fields.Selection([
        ('0', 'Faible'),
        ('1', 'Normal'),
        ('2', 'Élevé'),
        ('3', 'Urgent')
    ], string='Priorité', default='1', required=True)
    
    # Assignation
    technician_id = fields.Many2one('res.users', string='Technicien assigné', 
                                  domain=[('groups_id', 'in', 'intervention_management.group_intervention_technician')])
    dispatcher_id = fields.Many2one('res.users', string='Dispatcher', 
                                  default=lambda self: self.env.user)
    
    # Planification
    scheduled_date = fields.Datetime(string='Date planifiée')
    estimated_duration = fields.Float(string='Durée estimée (heures)', default=1.0)
    
    # Statut et progression
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('assigned', 'Assignée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('invoiced', 'Facturée'),
        ('cancelled', 'Annulée')
    ], string='Statut', default='draft', required=True, tracking=True)
    
    # Suivi de l'intervention
    start_date = fields.Datetime(string='Date de début')
    end_date = fields.Datetime(string='Date de fin')
    actual_duration = fields.Float(string='Durée réelle (heures)', compute='_compute_actual_duration', store=True)
    technician_notes = fields.Html(string='Notes du technicien')
    
    # Matériel utilisé
    product_ids = fields.Many2many('product.product', string='Produits utilisés')
    material_cost = fields.Monetary(string='Coût matériel', compute='_compute_material_cost', store=True)
    
    # Facturation
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    hourly_rate = fields.Monetary(string='Taux horaire', default=50.0)
    labor_cost = fields.Monetary(string='Coût main d\'œuvre', compute='_compute_labor_cost', store=True)
    total_cost = fields.Monetary(string='Coût total', compute='_compute_total_cost', store=True)
    
    # Facturation
    invoice_id = fields.Many2one('account.move', string='Facture')
    is_invoiced = fields.Boolean(string='Facturé', compute='_compute_is_invoiced', store=True)
    
    # Signature client
    client_signature = fields.Binary(string='Signature client')
    signature_date = fields.Datetime(string='Date de signature')
    
    @api.depends('start_date', 'end_date')
    def _compute_actual_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.actual_duration = delta.total_seconds() / 3600.0
            else:
                record.actual_duration = 0.0
    
    @api.depends('product_ids')
    def _compute_material_cost(self):
        for record in self:
            record.material_cost = sum(product.list_price for product in record.product_ids)
    
    @api.depends('actual_duration', 'hourly_rate')
    def _compute_labor_cost(self):
        for record in self:
            record.labor_cost = record.actual_duration * record.hourly_rate
    
    @api.depends('labor_cost', 'material_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.labor_cost + record.material_cost
    
    @api.depends('invoice_id')
    def _compute_is_invoiced(self):
        for record in self:
            record.is_invoiced = bool(record.invoice_id)
    
    def action_assign(self):
        """Assigner l'intervention à un technicien"""
        if not self.technician_id:
            raise ValidationError(_("Veuillez sélectionner un technicien avant d'assigner l'intervention."))
        self.state = 'assigned'
    
    def action_start(self):
        """Démarrer l'intervention"""
        self.start_date = fields.Datetime.now()
        self.state = 'in_progress'
    
    def action_complete(self):
        """Marquer l'intervention comme terminée"""
        if not self.start_date:
            self.start_date = fields.Datetime.now()
        self.end_date = fields.Datetime.now()
        self.state = 'completed'
    
    def action_create_invoice(self):
        """Créer une facture pour l'intervention"""
        if self.state != 'completed':
            raise ValidationError(_("L'intervention doit être terminée avant de pouvoir être facturée."))
        
        # Créer la facture
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'ref': f"Intervention - {self.title}",
            'invoice_line_ids': []
        }
        
        # Ligne pour la main d'œuvre
        if self.labor_cost > 0:
            labor_line = (0, 0, {
                'name': f"Main d'œuvre - {self.title} ({self.actual_duration}h)",
                'quantity': 1,
                'price_unit': self.labor_cost,
            })
            invoice_vals['invoice_line_ids'].append(labor_line)
        
        # Lignes pour les produits
        for product in self.product_ids:
            product_line = (0, 0, {
                'name': product.name,
                'product_id': product.id,
                'quantity': 1,
                'price_unit': product.list_price,
            })
            invoice_vals['invoice_line_ids'].append(product_line)
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        self.state = 'invoiced'
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_cancel(self):
        """Annuler l'intervention"""
        self.state = 'cancelled'