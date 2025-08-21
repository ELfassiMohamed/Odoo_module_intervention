{
    'name': 'Interventions',
    'version': '17.0.1.0.0',
    'category': '',
    'summary': 'Gestion des interventions techniques basée sur HelpDesk',
    'author': 'EL FASSI Mohamed',
    'depends': ['base', 'sale', 'account', 'hr'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/intervention_categories.xml',
        'views/intervention_request_views.xml',
        'views/intervention_menus.xml',
        'report/intervention_report_template.xml',
        'report/intervention_report.xml',
    ],
    'demo': [],
    'license': 'LGPL-3',

}