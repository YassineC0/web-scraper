# Dans app/config.py
SOURCES = [
    # ... autres sources ...
    {
        'id': 10,
        'name': 'FranceAgriMer - Passeport Semence Transport',
        'url': 'https://agent.expadon.fr/sites/infocom-site/accueil/recherche-avancee.html',
        'type': 'dynamic',
        'category': 'certification',
        'search_params': {
            'keywords': 'passeport semence transport exportation',
            'country': 'ALL',  # ou un pays spécifique
            'merchandise': 'semence',  # ou autre valeur du dropdown
            'file_type': None  # Laisser vide pour tous les types
        }
    },
    {
        'id': 11,
        'name': 'FranceAgriMer - Réglementation Semence',
        'url': 'https://agent.expadon.fr/sites/infocom-site/accueil/recherche-avancee.html',
        'type': 'dynamic',
        'category': 'certification',
        'search_params': {
            'keywords': 'réglementation semence certification',
            'country': 'UE',  # Union Européenne
            'merchandise': 'semence',
            'file_type': 'PDF'
        }
    }
]