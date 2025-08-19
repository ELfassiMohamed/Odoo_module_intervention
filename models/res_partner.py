from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Statistiques d'intervention
    intervention_count = fields.Integer(
        'Nombre d\'interventions',
        compute='_compute_intervention_stats'
    )
    
    last_intervention_date = fields.Datetime(
        'Dernière intervention',
        compute='_compute_intervention_stats'
    )
    
    total_intervention_cost = fields.Float(
        'Coût total interventions',
        compute='_compute_intervention_stats'
    )
    
    # Informations spécifiques
    equipment_type = fields.Char(
        'Type d\'équipement principal',
        help="Ex: Climatisation, Chauffage, etc."
    )
    
    access_instructions = fields.Text(
        'Instructions d\'accès',
        help="Instructions pour accéder aux locaux (codes, contact, etc.)"
    )

    @api.depends()
    def _compute_intervention_stats(self):
        for partner in self:
            tickets = self.env['helpdesk.ticket'].search([
                ('partner_id', '=', partner.id),
                ('is_intervention', '=', True)
            ])
            
            partner.intervention_count = len(tickets)
            partner.last_intervention_date = max(tickets.mapped('create_date'), default=False)
            partner.total_intervention_cost = sum(tickets.mapped('total_product_cost'))

    def action_view_interventions(self):
        """Voir toutes les interventions du client"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Interventions - {self.name}',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form,kanban',
            'domain': [
                ('partner_id', '=', self.id),
                ('is_intervention', '=', True)
            ],
            'context': {'default_partner_id': self.id, 'default_is_intervention': True}
        }

    def create_intervention_ticket(self, description, urgency='medium'):
        """Créer un ticket d'intervention pour ce client"""
        # Rechercher l'équipe d'intervention
        intervention_team = self.env['helpdesk.team'].search([
            ('is_intervention_team', '=', True)
        ], limit=1)
        
        if not intervention_team:
            raise UserError(_("Aucune équipe d'intervention configurée"))
        
        ticket_vals = {
            'name': f'Intervention - {self.name}',
            'description': description,
            'partner_id': self.id,
            'team_id': intervention_team.id,
            'is_intervention': True,
            'urgency_level': urgency,
            'intervention_address': f"{self.street or ''} {self.city or ''}"
        }
        
        return self.env['helpdesk.ticket'].create(ticket_vals)