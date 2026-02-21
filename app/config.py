
# AFRIFLOW/backend/app/config.py

import os
from dotenv import load_dotenv
from pathlib import Path

# Trouve le chemin absolu du dossier contenant ce fichier (app/)
BASE_DIR = Path(__file__).parent.absolute()
env_path = BASE_DIR / '.env'

# Charge les variables depuis le fichier .env
print(f"🔍 Chargement du .env depuis: {env_path}")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("✅ Fichier .env trouvé et chargé")
else:
    print(f"❌ Fichier .env non trouvé à: {env_path}")

# ============================================
# CONFIGURATION BASE DE DONNÉES
# ============================================
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    print(f"📊 DATABASE_URL chargée: {DATABASE_URL.split('@')[0].split('://')[0]}://****@...")
else:
    print("⚠️  DATABASE_URL non définie")
    # En production, on veut lever une erreur
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("DATABASE_URL must be set in production")

# ============================================
# CONFIGURATION REDIS (pour le worker)
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"

# ============================================
# CONFIGURATION JWT / AUTH
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_key_in_production")
if SECRET_KEY == "change_this_secret_key_in_production" and os.getenv("ENVIRONMENT") == "production":
    raise ValueError("SECRET_KEY must be changed in production")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 heures par défaut

# ============================================
# CONFIGURATION SMTP (EMAILS)
# ============================================
SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "user": os.getenv("SMTP_USER", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
    "from": os.getenv("SMTP_FROM", "noreply@afriflow.com"),
    "admin_email": os.getenv("SMTP_ADMIN", "admin@afriflow.com"),
    "enabled": os.getenv("SMTP_ENABLED", "false").lower() == "true"
}

# ============================================
# CONFIGURATION TWILIO (SMS)
# ============================================
TWILIO_CONFIG = {
    "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "phone_number": os.getenv("TWILIO_PHONE_NUMBER", ""),
    "enabled": all([
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"), 
        os.getenv("TWILIO_PHONE_NUMBER")
    ])
}

# ============================================
# CONFIGURATION PAIEMENTS MOBILE MONEY
# ============================================
ORANGE_MONEY_CONFIG = {
    "api_key": os.getenv("ORANGE_MONEY_API_KEY", ""),
    "api_secret": os.getenv("ORANGE_MONEY_SECRET", ""),
    "enabled": bool(os.getenv("ORANGE_MONEY_API_KEY"))
}

MTN_MONEY_CONFIG = {
    "api_key": os.getenv("MTN_MONEY_API_KEY", ""),
    "api_user": os.getenv("MTN_MONEY_API_USER", ""),
    "enabled": bool(os.getenv("MTN_MONEY_API_KEY"))
}

WAVE_CONFIG = {
    "api_key": os.getenv("WAVE_API_KEY", ""),
    "enabled": bool(os.getenv("WAVE_API_KEY"))
}

# ============================================
# CONFIGURATION AWS (pour les backups)
# ============================================
AWS_CONFIG = {
    "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
    "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
    "region": os.getenv("AWS_REGION", "eu-west-3"),  # Paris par défaut
    "bucket_name": os.getenv("AWS_BUCKET_NAME", "afriflow-backups"),
    "enabled": all([
        os.getenv("AWS_ACCESS_KEY_ID"),
        os.getenv("AWS_SECRET_ACCESS_KEY"),
        os.getenv("AWS_BUCKET_NAME")
    ])
}

# ============================================
# CONFIGURATION BACKUP
# ============================================
BACKUP_CONFIG = {
    "retention_days": int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
    "backup_time": os.getenv("BACKUP_TIME", "02:00"),  # 2h du matin
    "enabled": os.getenv("BACKUP_ENABLED", "true").lower() == "true"
}

# ============================================
# CONFIGURATION ENVIRONNEMENT
# ============================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ============================================
# CONFIGURATION CORS (Frontend)
# ============================================
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

# ============================================
# CONFIGURATION RATE LIMITING
# ============================================
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # en secondes

# ============================================
# CONFIGURATION SENTRY (Monitoring)
# ============================================
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "/data/logs/app.log")

print(f"✅ Configuration chargée - Environnement: {ENVIRONMENT}")

# ============================================
# FONCTIONS UTILITAIRES
# ============================================
def get_smtp_config():
    """Retourne la configuration SMTP"""
    return SMTP_CONFIG

def get_twilio_config():
    """Retourne la configuration Twilio"""
    return TWILIO_CONFIG

def get_payment_config(provider: str = None):
    """Retourne la configuration de paiement pour un provider spécifique"""
    providers = {
        "orange_money": ORANGE_MONEY_CONFIG,
        "mtn_money": MTN_MONEY_CONFIG,
        "wave": WAVE_CONFIG
    }
    if provider:
        return providers.get(provider, {})
    return providers

def is_production():
    """Vérifie si on est en production"""
    return ENVIRONMENT == "production"

def is_development():
    """Vérifie si on est en développement"""
    return ENVIRONMENT == "development"