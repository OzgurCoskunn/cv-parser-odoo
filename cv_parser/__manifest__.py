{
    'name': 'CV Parser - LLM',
    'version': '3.2',
    'author': 'ODE',
    'license': 'LGPL-3',
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/cv_parser_provider_views.xml',
        'views/cv_parser_config_views.xml',
        'views/openrouter_log_views.xml',
        'views/cv_parser_dashboard_views.xml',
        'views/hr_applicant_views.xml',
    ],
    'auto_install': False,
}
