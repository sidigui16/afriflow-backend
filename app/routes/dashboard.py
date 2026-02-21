
# AFRIFLOW/backend/app/routes/dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.auth import get_current_user
from app.models import models as db_models  # Un seul import pour tous les modèles

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/")
def dashboard_summary(
    business_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)  # Changement ici
):
    """Tableau de bord financier - peut être filtré par entreprise"""
    
    # Base query pour les transactions de l'utilisateur
    tx_query = db.query(db_models.Transaction).join(db_models.Business).filter(
        db_models.Business.owner_id == current_user.id
    )
    
    exp_query = db.query(db_models.Expense).join(db_models.Business).filter(
        db_models.Business.owner_id == current_user.id
    )
    
    # Filtrer par business si spécifié
    if business_id:
        # Vérifier que le business appartient à l'utilisateur
        business = db.query(db_models.Business).filter(
            db_models.Business.id == business_id,
            db_models.Business.owner_id == current_user.id
        ).first()
        if not business:
            raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce business")
        
        tx_query = tx_query.filter(db_models.Transaction.business_id == business_id)
        exp_query = exp_query.filter(db_models.Expense.business_id == business_id)
    
    # Récupérer toutes les transactions et dépenses
    transactions = tx_query.all()
    expenses = exp_query.all()
    
    # Calculs
    total_revenue = sum(t.amount for t in transactions)
    total_expenses = sum(e.amount for e in expenses)
    net_profit = total_revenue - total_expenses
    
    # Répartition par méthode de paiement
    cash_flow = {}
    for tx in transactions:
        method = tx.payment_method
        cash_flow[method] = cash_flow.get(method, 0) + tx.amount
    
    # Répartition par catégorie (dépenses)
    expenses_by_category = {}
    for exp in expenses:
        cat = exp.category
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + exp.amount
    
    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        },
        "cash_flow_by_method": cash_flow,
        "expenses_by_category": expenses_by_category,
        "counts": {
            "transactions": len(transactions),
            "expenses": len(expenses)
        }
    }