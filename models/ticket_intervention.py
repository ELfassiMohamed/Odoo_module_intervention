from odoo import models, fields, api, _
from odoo.exceptions import UserError
import math
from datetime import datetime, timedelta


class HelpdeskTicketIntervention(models.Model):
    _inherit = 'helpdesk.ticket'

    # Champs spécifiques aux interventions
    is_intervention = fields.Boolean(
        'Est une intervention',
        default=False,
        help="Cocher si ce ticket nécessite une intervention sur site"
    )
    
    urgency_level = fields.Selection([
        ('low', 'Normale'),
        ('medium', 'Moyenne'),
        ('high', 'Urgente'),
        ('critical', 'Critique - Panne totale')
    ], string='Niveau d\'urgence', default='medium')
    
    assigned_technician_id = fields.Many2one(
        'res.users',
        string='Technicien assigné',
        domain=[('is_intervention_technician', '=', True)]
    )
    
    intervention_address = fields.Text(
        'Adresse d\'intervention',
        help="Adresse où doit se rendre le technicien"
    )
    
    intervention_date = fields.Datetime('Date d\'intervention planifiée')
    intervention_start = fields.Datetime('Début intervention')
    intervention_end = fields.Datetime('Fin intervention')
    
    # Gestion des produits utilisés
    product_line_ids = fields.One2many(
        'intervention.product.line',
        'ticket_id',
        string='Pièces utilisées'
    )
    
    # Signature et validation
    client_signature = fields.Binary('Signature client')
    client_signature_date = fields.Datetime('Date signature')
    technician_notes = fields.Text('Notes du technicien')
    
    # Calculs automatiques
    total_product_cost = fields.Float(
        'Coût total pièces',
        compute='_compute_total_costs',
        store=True
    )
    intervention_duration = fields.Float(
        'Durée intervention (heures)',
        compute='_compute_intervention_duration',
        store=True
    )
    
    # Facturation
    invoice_created = fields.Boolean('Facture créée', default=False)
    invoice_id = fields.Many2one('account.move', 'Facture')

    @api.depends('product_line_ids.subtotal')
    def _compute_total_costs(self):
        for ticket in self:
            ticket.total_product_cost = sum(ticket.product_line_ids.mapped('subtotal'))

    @api.depends('intervention_start', 'intervention_end')
    def _compute_intervention_duration(self):
        for ticket in self:
            if ticket.intervention_start and ticket.intervention_end:
                delta = ticket.intervention_end - ticket.intervention_start
                ticket.intervention_duration = delta.total_seconds() / 3600
            else:
                ticket.intervention_duration = 0

    @api.model
    def create(self, vals):
        # Auto-assignation si c'est une intervention
        ticket = super().create(vals)
        if ticket.is_intervention and not ticket.assigned_technician_id:
            ticket.auto_assign_technician()
        return ticket

    def auto_assign_technician(self):
        """Attribution automatique du technicien le plus proche"""
        if not self.partner_id:
            raise UserError(_("Un client doit être défini pour l'auto-assignation"))
        
        # Recherche techniciens disponibles
        available_technicians = self.env['res.users'].search([
            ('is_intervention_technician', '=', True),
            ('technician_available', '=', True)
        ])
        
        if not available_technicians:
            raise UserError(_("Aucun technicien disponible trouvé"))
        
        # Si un seul technicien, on l'assigne directement
        if len(available_technicians) == 1:
            self.assigned_technician_id = available_technicians[0]
        else:
            # Logique de proximité (simplifiée pour la démo)
            # Ici vous pouvez ajouter une logique plus complexe basée sur la géolocalisation
            self.assigned_technician_id = available_technicians[0]
        
        # Marquer le technicien comme occupé
        self.assigned_technician_id.technician_available = False
        
        # Envoyer notification
        self.send_technician_notification()

    def send_technician_notification(self):
        """Envoi de notification au technicien"""
        if self.assigned_technician_id:
            # Création d'une activité pour le technicien
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.assigned_technician_id.id,
                summary=f"Intervention {self.urgency_level}: {self.name}",
                note=f"Nouvelle intervention assignée.\nClient: {self.partner_id.name}\nAdresse: {self.intervention_address}"
            )

    def action_start_intervention(self):
        """Démarrage de l'intervention"""
        if not self.assigned_technician_id:
            raise UserError(_("Aucun technicien assigné"))
        
        self.intervention_start = fields.Datetime.now()
        # Trouver l'étape "En cours"
        stage_in_progress = self.env['helpdesk.stage'].search([
            ('name', 'ilike', 'en cours'),
            ('team_ids', 'in', self.team_id.ids)
        ], limit=1)
        if stage_in_progress:
            self.stage_id = stage_in_progress.id

    def action_complete_intervention(self):
        """Finalisation de l'intervention"""
        if not self.intervention_start:
            raise UserError(_("L'intervention doit être démarrée avant d'être finalisée"))
        
        self.intervention_end = fields.Datetime.now()
        
        # Trouver l'étape "Terminé"
        stage_completed = self.env['helpdesk.stage'].search([
            ('name', 'ilike', 'terminé'),
            ('team_ids', 'in', self.team_id.ids)
        ], limit=1)
        if stage_completed:
            self.stage_id = stage_completed.id
        
        # Libérer le technicien
        if self.assigned_technician_id:
            self.assigned_technician_id.technician_available = True
        
        # Générer la facture automatiquement
        self.action_generate_invoice()

    def action_generate_invoice(self):
        """Génération automatique de la facture"""
        if self.invoice_created:
            raise UserError(_("La facture a déjà été créée"))
        
        if not self.partner_id:
            raise UserError(_("Un client doit être défini"))
        
        # Création de la facture
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'ref': self.name,
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Ligne de service (main d'œuvre)
        if self.intervention_duration > 0:
            # Utiliser un produit de service par défaut ou en créer un
            service_product = self.env['product.product'].search([
                ('name', 'ilike', 'intervention'),
                ('type', '=', 'service')
            ], limit=1)
            
            if not service_product:
                # Créer un produit de service par défaut
                service_product = self.env['product.product'].create({
                    'name': 'Service d\'intervention technique',
                    'type': 'service',
                    'list_price': 50.0,  # Prix par heure par défaut
                    'uom_id': self.env.ref('uom.product_uom_hour').id,
                    'uom_po_id': self.env.ref('uom.product_uom_hour').id,
                })
            
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': service_product.id,
                'name': f'Intervention technique - {self.name}',
                'quantity': self.intervention_duration,
                'price_unit': service_product.list_price,
                'account_id': service_product.property_account_income_id.id or self.env['account.account'].search([('code', '=like', '70%')], limit=1).id,
            })
        
        # Lignes pour les pièces utilisées
        for product_line in self.product_line_ids:
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': product_line.product_id.id,
                'name': product_line.product_id.name,
                'quantity': product_line.quantity,
                'price_unit': product_line.unit_price,
                'account_id': product_line.product_id.property_account_income_id.id or self.env['account.account'].search([('code', '=like', '70%')], limit=1).id,
            })
        
        self.invoice_id = invoice.id
        self.invoice_created = True
        
        # Trouver l'étape "Facturé"
        stage_invoiced = self.env['helpdesk.stage'].search([
            ('name', 'ilike', 'facturé'),
            ('team_ids', 'in', self.team_id.ids)
        ], limit=1)
        if stage_invoiced:
            self.stage_id = stage_invoiced.id
        
        # Envoyer la facture par email
        self.send_invoice_by_email()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture générée',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def send_invoice_by_email(self):
        """Envoi de la facture par email"""
        if self.invoice_id and self.partner_id.email:
            template = self.env.ref('account.email_template_edi_invoice', False)
            if template:
                template.send_mail(self.invoice_id.id, force_send=True)