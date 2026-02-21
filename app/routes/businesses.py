
# AFRIFLOW/backend/app/routes/businesses.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import models as db_models  # Changement ici
from app.schemas import schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/businesses", tags=["businesses"])

@router.post("/", response_model=schemas.BusinessOut)
def create_business(
    business: schemas.BusinessCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)  # Changement ici
):
    """Créer une nouvelle entreprise pour l'utilisateur connecté"""
    new_business = db_models.Business(
        **business.model_dump(),
        owner_id=current_user.id
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return new_business

@router.get("/", response_model=List[schemas.BusinessOut])
def get_user_businesses(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Récupérer toutes les entreprises de l'utilisateur connecté"""
    businesses = db.query(db_models.Business).filter(
        db_models.Business.owner_id == current_user.id
    ).all()
    return businesses

@router.get("/{business_id}", response_model=schemas.BusinessWithDetails)
def get_business_details(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Récupérer les détails d'une entreprise spécifique"""
    business = db.query(db_models.Business).filter(
        db_models.Business.id == business_id,
        db_models.Business.owner_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Entreprise non trouvée")
    
    # Calculer les statistiques
    transactions = db.query(db_models.Transaction).filter(
        db_models.Transaction.business_id == business_id
    ).all()
    
    expenses = db.query(db_models.Expense).filter(
        db_models.Expense.business_id == business_id
    ).all()
    
    total_revenue = sum(t.amount for t in transactions)
    total_expenses = sum(e.amount for e in expenses)
    
    return {
        **business.__dict__,
        "transactions_count": len(transactions),
        "expenses_count": len(expenses),
        "total_revenue": total_revenue,
        "total_expenses": total_expenses
    }

@router.delete("/{business_id}")
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Supprimer une entreprise"""
    business = db.query(db_models.Business).filter(
        db_models.Business.id == business_id,
        db_models.Business.owner_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Entreprise non trouvée")
    
    db.delete(business)
    db.commit()
    return {"message": "Entreprise supprimée avec succès"}