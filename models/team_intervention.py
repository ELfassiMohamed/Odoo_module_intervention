from odoo import models, fields, api, _


class HelpdeskTeamIntervention(models.Model):
    _inherit = 'helpdesk.team'

    # Champs spécifiques aux équipes d'intervention
    is_intervention_team = fields.Boolean(
        'Équipe d\'intervention',
        default=False,
        help="Cette équipe gère les interventions sur site"
    )
    
    auto_assign_technician = fields.Boolean(
        'Assignation automatique',
        default=True,
        help="Assigner automatiquement un technicien aux nouveaux tickets"
    )
    
    default_intervention_duration = fields.Float(
        'Durée d\'intervention par défaut (heures)',
        default=2.0,
        help="Durée estimée par défaut pour une intervention"
    )
    
    # Statistiques de l'équipe
    intervention_count = fields.Integer(
        'Interventions totales',
        compute='_compute_intervention_stats'
    )
    
    pending_interventions = fields.Integer(
        'Interventions en attente',
        compute='_compute_intervention_stats'
    )
    
    available_technicians = fields.Integer(
        'Techniciens disponibles',
        compute='_compute_technician_stats'
    )

    @api.depends('ticket_ids')
    def _compute_intervention_stats(self):
        for team in self:
            interventions = team.ticket_ids.filtered('is_intervention')
            team.intervention_count = len(interventions)
            team.pending_interventions = len(interventions.filtered(
                lambda t: t.stage_id.name in ['Nouveau', 'Assigné', 'En attente']
            ))

    def _compute_technician_stats(self):
        for team in self:
            if team.is_intervention_team:
                technicians = self.env['res.users'].search([
                    ('is_intervention_technician', '=', True),
                    ('technician_available', '=', True)
                ])
                team.available_technicians = len(technicians)
            else:
                team.available_technicians = 0


class HelpdeskStageIntervention(models.Model):
    _inherit = 'helpdesk.stage'

    # Spécifique aux interventions
    is_intervention_stage = fields.Boolean(
        'Étape d\'intervention',
        default=False,
        help="Cette étape est spécifique aux interventions"
    )
    
    auto_actions = fields.Selection([
        ('none', 'Aucune'),
        ('assign', 'Assigner technicien'),
        ('notify', 'Notifier technicien'),
        ('start', 'Démarrer intervention'),
        ('invoice', 'Générer facture')
    ], string='Action automatique', default='none')
    
    require_signature = fields.Boolean(
        'Signature requise',
        default=False,
        help="Une signature client est requise pour passer à cette étape"
    )

    def write(self, vals):
        """Surcharge pour déclencher les actions automatiques"""
        result = super().write(vals)
        
        # Si on change l'étape d'un ticket d'intervention
        if 'ticket_ids' in vals:
            for stage in self:
                if stage.auto_actions != 'none':
                    tickets = stage.ticket_ids.filtered('is_intervention')
                    for ticket in tickets:
                        stage._execute_auto_action(ticket)
        
        return result

    def _execute_auto_action(self, ticket):
        """Exécuter l'action automatique pour un ticket"""
        if self.auto_actions == 'assign' and not ticket.assigned_technician_id:
            ticket.auto_assign_technician()
        elif self.auto_actions == 'notify' and ticket.assigned_technician_id:
            ticket.send_technician_notification()
        elif self.auto_actions == 'start':
            if not ticket.intervention_start:
                ticket.action_start_intervention()
        elif self.auto_actions == 'invoice':
            if not ticket.invoice_created:
                ticket.action_generate_invoice()