{
    'name': 'Interventions',
    'version': '17.0.1.0.0',
    'category': '',
    'summary': 'Gestion des interventions techniques basée sur HelpDesk',
    'description': """
        Module de gestion des interventions techniques
        =============================================
        
        * Extension du module HelpDesk pour les interventions sur site
        * Attribution automatique des techniciens
        * Gestion des pièces de rechange
        * Signature numérique client
        * Génération automatique de factures
        
        Cas d'usage: Maintenance climatiseurs, réparations, installations
    """,
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
    ],
    'demo': [
        'demo/intervention_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}