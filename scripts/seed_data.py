
# AFRIFLOW/backend/scripts/seed_data.py : script pour générer des données de test

#!/usr/bin/env python
"""Script pour générer des données de test réalistes"""

import random
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import models
from app.auth import hash_password

def generate_test_data():
    """Génère des données de test pour la démo"""
    db = SessionLocal()
    
    # Créer un utilisateur de démo
    demo_user = models.User(
        email="demo@afriflow.com",
        password_hash=hash_password("demo123")
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    
    # Créer plusieurs businesses
    businesses = []
    for i in range(3):
        business = models.Business(
            name=f"Entreprise {i+1}",
            sector=random.choice(["Commerce", "Service", "Agriculture"]),
            currency="FCFA",
            owner_id=demo_user.id
        )
        db.add(business)
        businesses.append(business)
    db.commit()
    
    # Générer des transactions sur 6 mois
    categories = ["Vente", "Service", "Produit"]
    methods = ["cash", "mobile_money", "card"]
    
    for business in businesses:
        for days_ago in range(180):
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # 1-3 transactions par jour
            for _ in range(random.randint(1, 3)):
                transaction = models.Transaction(
                    amount=random.randint(5000, 200000),
                    payment_method=random.choice(methods),
                    category=random.choice(categories),
                    description="Vente",
                    created_at=date,
                    business_id=business.id
                )
                db.add(transaction)
            
            # Dépenses 2-3 fois par semaine
            if random.random() < 0.3:
                expense = models.Expense(
                    amount=random.randint(10000, 50000),
                    category=random.choice(["Loyer", "Salaires", "Fournitures", "Transport"]),
                    description="Dépense",
                    created_at=date,
                    business_id=business.id
                )
                db.add(expense)
    
    db.commit()
    print("✅ Données de test générées avec succès!")
    print(f"👤 Utilisateur de démo: demo@afriflow.com / demo123")
    
if __name__ == "__main__":
    generate_test_data()