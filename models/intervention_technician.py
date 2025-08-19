from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Champs spécifiques aux techniciens
    is_intervention_technician = fields.Boolean(
        'Est un technicien d\'intervention',
        default=False,
        help="Cocher si cet utilisateur peut réaliser des interventions"
    )
    
    technician_available = fields.Boolean(
        'Disponible',
        default=True,
        help="Indique si le technicien est disponible pour de nouvelles interventions"
    )
    
    specialty_ids = fields.Many2many(
        'intervention.specialty',
        string='Spécialités',
        help="Spécialités du technicien (climatisation, plomberie, etc.)"
    )
    
    current_location = fields.Char(
        'Position actuelle',
        help="Adresse ou position GPS du technicien"
    )
    
    # Statistiques
    intervention_count = fields.Integer(
        'Nombre d\'interventions',
        compute='_compute_intervention_stats'
    )
    
    current_interventions = fields.Integer(
        'Interventions en cours',
        compute='_compute_intervention_stats'
    )

    @api.depends('is_intervention_technician')
    def _compute_intervention_stats(self):
        for user in self:
            if user.is_intervention_technician:
                tickets = self.env['helpdesk.ticket'].search([
                    ('assigned_technician_id', '=', user.id),
                    ('is_intervention', '=', True)
                ])
                user.intervention_count = len(tickets)
                user.current_interventions = len(tickets.filtered(
                    lambda t: t.stage_id.name in ['En cours', 'Assigné']
                ))
            else:
                user.intervention_count = 0
                user.current_interventions = 0

    def action_view_interventions(self):
        """Action pour voir les interventions du technicien"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mes Interventions',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form,kanban',
            'domain': [
                ('assigned_technician_id', '=', self.id),
                ('is_intervention', '=', True)
            ],
            'context': {'default_assigned_technician_id': self.id}
        }

    def mark_available(self):
        """Marquer le technicien comme disponible"""
        self.technician_available = True

    def mark_busy(self):
        """Marquer le technicien comme occupé"""
        self.technician_available = False


class InterventionSpecialty(models.Model):
    _name = 'intervention.specialty'
    _description = 'Spécialité d\'intervention'

    name = fields.Char('Nom', required=True)
    description = fields.Text('Description')
    color = fields.Integer('Couleur', default=1)

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]