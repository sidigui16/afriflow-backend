
# AFRIFLOW/backend/tests/test_analytics.py : Test pour les analytics

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from datetime import datetime, timedelta
import time

# Base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestAnalytics:
    def setup_method(self):
        """Créer les tables avant chaque test"""
        Base.metadata.create_all(bind=engine)
        
        # Utiliser l'email principal
        self.test_email = "boubacardiallo160590@gmail.com"
        self.test_password = "Test123!"
        
        # Créer un utilisateur et récupérer le token
        self._create_test_user()
        self.token = self._get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Créer un business
        self.business_id = self._create_test_business()
        
        # Ajouter des données de test
        self._add_test_data()
    
    def teardown_method(self):
        """Supprimer les tables après chaque test"""
        Base.metadata.drop_all(bind=engine)
    
    def _create_test_user(self):
        """Créer un utilisateur de test"""
        response = client.post("/users/register", json={
            "email": self.test_email,
            "password": self.test_password
        })
        # Si l'utilisateur existe déjà, c'est pas grave
        return response.json() if response.status_code == 200 else None
    
    def _get_token(self):
        """Récupérer le token d'authentification"""
        response = client.post("/users/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def _create_test_business(self):
        """Créer une entreprise de test"""
        response = client.post("/businesses/", 
            json={"name": "Test Business Analytics", "sector": "Tech"},
            headers=self.headers
        )
        assert response.status_code == 200
        return response.json()["id"]
    
    def _add_test_data(self):
        """Ajouter des transactions et dépenses de test"""
        # Ajouter des transactions sur différents mois
        current_date = datetime.now()
        
        # Transactions du mois en cours (10 transactions)
        for i in range(10):
            tx_response = client.post("/transactions/", 
                json={
                    "amount": 100000 + (i * 10000),
                    "payment_method": "mobile_money" if i % 2 == 0 else "cash",
                    "category": f"Catégorie {i % 3}",
                    "description": f"Transaction test {i}",
                    "business_id": self.business_id
                },
                headers=self.headers
            )
            assert tx_response.status_code == 200
        
        # Transactions du mois dernier (5 transactions)
        for i in range(5):
            # Note: on ne peut pas facilement dater les transactions via l'API
            # On les crée normalement, elles auront la date courante
            tx_response = client.post("/transactions/", 
                json={
                    "amount": 50000 + (i * 5000),
                    "payment_method": "cash",
                    "category": "Vente",
                    "description": f"Ancienne transaction {i}",
                    "business_id": self.business_id
                },
                headers=self.headers
            )
            assert tx_response.status_code == 200
        
        # Dépenses par catégorie
        expense_categories = ["Loyer", "Salaires", "Fournitures", "Transport", "Marketing"]
        for category in expense_categories:
            exp_response = client.post("/expenses/",
                json={
                    "amount": 50000,
                    "category": category,
                    "description": f"Dépense {category}",
                    "business_id": self.business_id
                },
                headers=self.headers
            )
            assert exp_response.status_code == 200
        
        # Quelques dépenses supplémentaires pour varier les montants
        extra_expenses = [
            ("Loyer", 150000),
            ("Salaires", 300000),
            ("Fournitures", 75000)
        ]
        for category, amount in extra_expenses:
            client.post("/expenses/",
                json={
                    "amount": amount,
                    "category": category,
                    "description": f"Dépense supplémentaire {category}",
                    "business_id": self.business_id
                },
                headers=self.headers
            )
    
    # ========== TESTS DES ENDPOINTS ANALYTICS ==========
    
    def test_monthly_revenue(self):
        """Test des revenus mensuels"""
        response = client.get(
            f"/analytics/{self.business_id}/monthly-revenue",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Vérifier la structure des données
        first_item = data[0]
        assert "month_num" in first_item
        assert "month_name" in first_item
        assert "total" in first_item
        assert "transaction_count" in first_item
        
        # Vérifier les types
        assert isinstance(first_item["month_num"], int)
        assert isinstance(first_item["month_name"], str)
        assert isinstance(first_item["total"], (int, float))
        assert isinstance(first_item["transaction_count"], int)
    
    def test_monthly_revenue_with_year_filter(self):
        """Test des revenus mensuels avec filtre année"""
        current_year = datetime.now().year
        response = client.get(
            f"/analytics/{self.business_id}/monthly-revenue?year={current_year}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_expenses_by_category(self):
        """Test des dépenses par catégorie"""
        response = client.get(
            f"/analytics/{self.business_id}/expenses-by-category",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Vérifier la structure
        first_item = data[0]
        assert "category" in first_item
        assert "total" in first_item
        assert "count" in first_item
        assert "percentage" in first_item
        
        # Vérifier que les pourcentages sont entre 0 et 100
        assert 0 <= first_item["percentage"] <= 100
        
        # Vérifier que la somme des pourcentages est proche de 100
        total_percentage = sum(item["percentage"] for item in data)
        assert abs(total_percentage - 100) < 1  # Marge d'erreur de 1%
    
    def test_payment_methods(self):
        """Test de distribution des méthodes de paiement"""
        response = client.get(
            f"/analytics/{self.business_id}/payment-methods",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Vérifier la structure
        first_item = data[0]
        assert "method" in first_item
        assert "method_name" in first_item
        assert "total" in first_item
        assert "count" in first_item
        assert "percentage" in first_item
        
        # Vérifier que les méthodes de paiement sont valides
        valid_methods = ["cash", "mobile_money", "card", "bank_transfer"]
        assert first_item["method"] in valid_methods
    
    def test_top_categories(self):
        """Test des top catégories"""
        response = client.get(
            f"/analytics/{self.business_id}/top-categories?limit=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier la structure
        assert "top_sales_categories" in data
        assert "top_expense_categories" in data
        
        # Vérifier que les listes ne sont pas vides
        assert len(data["top_sales_categories"]) > 0
        assert len(data["top_expense_categories"]) > 0
        
        # Vérifier la structure des catégories
        sales_cat = data["top_sales_categories"][0]
        assert "category" in sales_cat
        assert "total" in sales_cat
        assert "count" in sales_cat
    
    def test_daily_stats(self):
        """Test des statistiques journalières"""
        response = client.get(
            f"/analytics/{self.business_id}/daily-stats?days=30",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier la structure
        assert "daily_data" in data
        assert "summary" in data
        
        # Vérifier daily_data
        daily_data = data["daily_data"]
        assert isinstance(daily_data, list)
        if len(daily_data) > 0:
            first_day = daily_data[0]
            assert "date" in first_day
            assert "revenue" in first_day
            assert "expenses" in first_day
            assert "profit" in first_day
        
        # Vérifier summary
        summary = data["summary"]
        assert "total_revenue" in summary
        assert "total_expenses" in summary
        assert "total_profit" in summary
        assert "profit_margin" in summary
        assert "avg_daily_revenue" in summary
        assert "days_count" in summary
        
        # Vérifier la cohérence
        assert summary["total_revenue"] >= 0
        assert summary["days_count"] <= 30
    
    def test_comparative_stats(self):
        """Test des statistiques comparatives"""
        current_year = datetime.now().year
        response = client.get(
            f"/analytics/{self.business_id}/comparative/{current_year}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier la structure
        assert "year" in data
        assert "previous_year" in data
        assert "monthly_comparison" in data
        assert "year_over_year_growth" in data
        
        # Vérifier que l'année est correcte
        assert data["year"] == current_year
        assert data["previous_year"] == current_year - 1
    
    def test_cash_flow_analysis(self):
        """Test de l'analyse du cash flow"""
        response = client.get(
            f"/analytics/{self.business_id}/cash-flow-analysis",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier la structure
        assert "monthly_breakdown" in data
        
        monthly_data = data["monthly_breakdown"]
        assert isinstance(monthly_data, list)
        
        if len(monthly_data) > 0:
            first_month = monthly_data[0]
            assert "period" in first_month
            assert "cash" in first_month
            assert "mobile_money" in first_month
            assert "total" in first_month
    
    def test_complete_dashboard(self):
        """Test du dashboard complet"""
        response = client.get(
            f"/analytics/{self.business_id}/dashboard",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier toutes les sections du dashboard
        assert "business_info" in data
        assert "monthly_revenue" in data
        assert "expenses_by_category" in data
        assert "payment_methods" in data
        assert "top_categories" in data
        assert "daily_stats" in data
        assert "cash_flow" in data
        
        # Vérifier business_info
        business_info = data["business_info"]
        assert "id" in business_info
        assert "name" in business_info
        assert business_info["id"] == self.business_id
    
    # ========== TESTS DE PERFORMANCE ==========
    
    def test_dashboard_performance(self):
        """Test de performance du dashboard"""
        # Mesurer le temps de réponse
        start_time = time.time()
        response = client.get(
            f"/analytics/{self.business_id}/dashboard",
            headers=self.headers
        )
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code == 200
        # Le dashboard complet devrait répondre en moins de 2 secondes
        assert duration < 2.0
    
    # ========== TESTS D'ERREUR ==========
    
    def test_invalid_business_id(self):
        """Test avec un ID d'entreprise invalide"""
        response = client.get(
            "/analytics/99999/monthly-revenue",
            headers=self.headers
        )
        assert response.status_code == 403  # Non autorisé ou pas trouvé
    
    def test_unauthorized_access(self):
        """Test d'accès sans authentification"""
        response = client.get(
            f"/analytics/{self.business_id}/monthly-revenue"
        )
        assert response.status_code == 401  # Non authentifié
    
    def test_invalid_date_range(self):
        """Test avec une plage de dates invalide"""
        # days > 365 devrait être rejeté
        response = client.get(
            f"/analytics/{self.business_id}/daily-stats?days=500",
            headers=self.headers
        )
        # Soit 200 (avec limitation automatique) soit 422 (validation)
        assert response.status_code in [200, 422]
    
    def test_negative_days(self):
        """Test avec des jours négatifs"""
        response = client.get(
            f"/analytics/{self.business_id}/daily-stats?days=-10",
            headers=self.headers
        )
        # Devrait être rejeté
        assert response.status_code in [400, 422]