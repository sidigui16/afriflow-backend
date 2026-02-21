
# AFRIFLOW/backend/app/config/constants.py

# Constantes pour l'application
MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

PAYMENT_METHODS = {
    "cash": "Espèces",
    "mobile_money": "Mobile Money",
    "card": "Carte bancaire",
    "bank_transfer": "Virement"
}

CURRENCIES = ["FCFA", "EUR", "USD", "NGN", "GHS", "KES"]

# Seuils et limites
MAX_BUSINESSES_PER_USER = 10
MAX_TRANSACTIONS_PER_PAGE = 100
DEFAULT_DATE_RANGE_DAYS = 30