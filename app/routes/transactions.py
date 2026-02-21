
# AFRIFLOW/backend/app/routes/transactions.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import models as db_models  # Changement ici : import explicite
from app.schemas import schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/", response_model=schemas.TransactionOut)
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)  # Changement ici
):
    """Créer une nouvelle transaction (protégée par JWT)"""
    # Vérifier que le business appartient bien à l'utilisateur
    business = db.query(db_models.Business).filter(
        db_models.Business.id == transaction.business_id,
        db_models.Business.owner_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce business")
    
    new_tx = db_models.Transaction(**transaction.model_dump())
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return new_tx

@router.get("/", response_model=List[schemas.TransactionOut])
def get_transactions(
    business_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Récupérer les transactions (filtrées par business si spécifié)"""
    query = db.query(db_models.Transaction).join(
        db_models.Business
    ).filter(
        db_models.Business.owner_id == current_user.id
    )
    
    if business_id:
        # Vérifier que le business appartient à l'utilisateur
        business = db.query(db_models.Business).filter(
            db_models.Business.id == business_id,
            db_models.Business.owner_id == current_user.id
        ).first()
        if not business:
            raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce business")
        query = query.filter(db_models.Transaction.business_id == business_id)
    
    return query.all()

@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Récupérer une transaction spécifique"""
    transaction = db.query(db_models.Transaction).join(
        db_models.Business
    ).filter(
        db_models.Transaction.id == transaction_id,
        db_models.Business.owner_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction non trouvée")
    
    return transaction