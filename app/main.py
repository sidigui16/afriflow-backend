
# AFRIFLOW/backend/app/main.py

from contextlib import asynccontextmanager  
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, transactions, expenses, dashboard, businesses, analytics
from app.database import engine, Base, check_connection, create_tables
import logging
import datetime
import sys
import fastapi
import sqlalchemy

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 👇 NOUVELLE FONCTION LIFESPAN (remplace les events startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP (ancien @app.on_event("startup")) ---
    logger.info("🚀 Démarrage de l'API Afriflow...")
    
    # Vérification de la connexion à la base de données
    if check_connection():
        logger.info("✅ Connexion à la base de données établie")
        
        # Création des tables si elles n'existent pas (développement seulement)
        # En production, utiliser Alembic pour les migrations
        create_tables()
    else:
        logger.error("❌ Impossible de se connecter à la base de données")
        # En production, on pourrait vouloir arrêter l'application
        # raise Exception("Database connection failed")
    
    yield  # 👈 L'application tourne ici
    
    # --- SHUTDOWN (ancien @app.on_event("shutdown")) ---
    logger.info("👋 Arrêt de l'API Afriflow")
    # Vous pouvez ajouter ici du nettoyage si nécessaire
    # Par exemple: fermer des connexions, libérer des ressources

# Initialisation de l'application FastAPI avec le nouveau système lifespan
app = FastAPI(
    title="Afriflow API",
    description="API de gestion financière pour entreprises africaines",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    lifespan=lifespan,  # 👈 C'EST LA CLÉ ! Activation du nouveau système
    openapi_tags=[  # Documentation des tags
        {
            "name": "users",
            "description": "Opérations d'authentification et gestion des utilisateurs"
        },
        {
            "name": "businesses", 
            "description": "Gestion des entreprises (multi-tenant)"
        },
        {
            "name": "transactions",
            "description": "Gestion des transactions / revenus"
        },
        {
            "name": "expenses",
            "description": "Gestion des dépenses"
        },
        {
            "name": "dashboard",
            "description": "Tableau de bord synthétique"
        },
        {
            "name": "analytics",
            "description": "Analytics avancées et graphiques 📊"
        }
    ]
)

# Configuration CORS pour permettre au frontend d'accéder à l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production: ["https://monapp.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
app.include_router(users.router)
app.include_router(businesses.router)
app.include_router(transactions.router)
app.include_router(expenses.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    """
    Racine de l'API - Informations générales
    """
    return {
        "success": True,
        "message": "Afriflow backend opérationnel 🚀",
        "version": app.version,
        "environment": "development",  # À changer en production
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "features": [
            "✅ Authentification JWT",
            "✅ Multi-entreprises",
            "✅ Transactions & Dépenses",
            "✅ Dashboard temps réel",
            "✅ Analytics avancées 📊",
            "✅ Comparaisons annuelles",
            "🔜 Prévisions ML",
            "🔜 Intégrations paiements africains"
        ],
        "endpoints": {
            "users": "/users",
            "businesses": "/businesses",
            "transactions": "/transactions", 
            "expenses": "/expenses",
            "dashboard": "/dashboard",
            "analytics": "/analytics",
            "docs": "/docs"
        },
        "health_check": "/health"
    }

@app.get("/health")
def health_check():
    """
    Endpoint de santé pour le monitoring
    """
    db_status = check_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": app.version,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/info")
def info():
    """
    Informations détaillées sur l'API
    """
    return {
        "name": app.title,
        "description": app.description,
        "version": app.version,
        "python_version": sys.version,
        "fastapi_version": fastapi.__version__,
        "sqlalchemy_version": sqlalchemy.__version__,
        "environment": "development"
    }