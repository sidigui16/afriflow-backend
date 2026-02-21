
# AFRIFLOW/backend/app/routes/analytics.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models import models
from app.services.analytics_service import AnalyticsService
from datetime import datetime

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/{business_id}/monthly-revenue")
def get_monthly_revenue(
    business_id: int,
    year: Optional[int] = Query(None, description="Année spécifique"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Revenus mensuels avec détails"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_monthly_revenue(year)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/expenses-by-category")
def get_expenses_by_category(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Dépenses par catégorie avec pourcentages"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_expenses_by_category()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/payment-methods")
def get_payment_methods(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Distribution des méthodes de paiement"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_payment_methods_distribution()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/top-categories")
def get_top_categories(
    business_id: int,
    limit: int = Query(5, description="Nombre de catégories à retourner"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Top catégories de ventes et dépenses"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_top_categories(limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/daily-stats")
def get_daily_stats(
    business_id: int,
    days: int = Query(30, description="Nombre de jours à analyser", ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Statistiques journalières pour graphiques"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_daily_stats(days)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/comparative/{year}")
def get_comparative_stats(
    business_id: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Statistiques comparatives avec année précédente"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_comparative_stats(year)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/cash-flow-analysis")
def get_cash_flow_analysis(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Analyse détaillée du cash flow"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_cash_flow_analysis()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/summary")
def get_summary_stats(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Résumé des statistiques clés"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        return service.get_summary_stats()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{business_id}/dashboard")
def get_complete_dashboard(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Dashboard complet avec toutes les analytics"""
    try:
        service = AnalyticsService(db, business_id, current_user.id)
        
        # Récupérer le nom du business avec la nouvelle syntaxe SQLAlchemy 2.0
        business = db.query(models.Business).filter(
            models.Business.id == business_id,
            models.Business.owner_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business non trouvé")
        
        # Récupérer toutes les stats
        return {
            "business_info": {
                "id": business_id,
                "name": business.name,
                "currency": business.currency,
                "sector": business.sector
            },
            "monthly_revenue": service.get_monthly_revenue(),
            "expenses_by_category": service.get_expenses_by_category(),
            "payment_methods": service.get_payment_methods_distribution(),
            "top_categories": service.get_top_categories(),
            "daily_stats": service.get_daily_stats(30),
            "cash_flow": service.get_cash_flow_analysis(),
            "summary": service.get_summary_stats()
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))