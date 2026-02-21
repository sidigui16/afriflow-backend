
# AFRIFLOW/backend/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de la connexion à la base de données
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,  # Nombre de connexions permanentes
        max_overflow=10,  # Connexions supplémentaires temporaires
        pool_pre_ping=True,  # Vérifie que la connexion est vivante avant utilisation
        echo=False  # Met à True pour voir les requêtes SQL dans la console
    )
    logger.info("✅ Connexion à la base de données établie avec succès")
except Exception as e:
    logger.error(f"❌ Erreur de connexion à la base de données: {e}")
    raise

# Session pour interagir avec la base
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base pour créer les modèles (tables)
Base = declarative_base()

# Dependency pour FastAPI
def get_db():
    """
    Dépendance FastAPI pour obtenir une session de base de données.
    À utiliser dans les routes avec: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fonction utilitaire pour créer les tables (optionnel)
def create_tables():
    """Crée toutes les tables définies dans les modèles"""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables créées/vérifiées avec succès")

# Fonction utilitaire pour supprimer les tables (attention en production!)
def drop_tables():
    """Supprime toutes les tables (UTILISER AVEC PRÉCAUTION)"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("⚠️ Toutes les tables ont été supprimées")

# Fonction pour vérifier la connexion
def check_connection():
    """Vérifie que la connexion à la base fonctionne"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion: {e}")
        return False

