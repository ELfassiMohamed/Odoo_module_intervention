{
    'name': 'Interventions',
    'version': '17.0.1.0.0',
    'category': '',
    'summary': 'Gestion des interventions techniques basée sur HelpDesk',
    'author': 'EL FASSI Mohamed',
   'depends': [
        'helpdesk',
        'stock',
        'account',
        'hr',
        'base_geolocalize'
    ],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',
        
        # Données
        'data/helpdesk_teams_data.xml',
        'data/helpdesk_stages_data.xml',
        'data/intervention_sequences.xml',
        
        # Vues
        'views/ticket_intervention_views.xml',
        'views/intervention_technician_views.xml',
        'views/intervention_product_line_views.xml',
        'views/intervention_menus.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/intervention_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}