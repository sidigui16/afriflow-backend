
# AFRIFLOW/backend/app/routes/expenses.py


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import models as db_models
from app.schemas import schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])

@router.post("/", response_model=schemas.ExpenseOut)
def create_expense(
    expense: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)  # Changé de models.User à db_models.User
):
    # Vérifier l'accès au business
    business = db.query(db_models.Business).filter(
        db_models.Business.id == expense.business_id,
        db_models.Business.owner_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce business")
    
    new_exp = db_models.Expense(**expense.model_dump())
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    return new_exp

@router.get("/", response_model=List[schemas.ExpenseOut])
def get_expenses(
    business_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)  # Changé aussi ici
):
    query = db.query(db_models.Expense).join(
        db_models.Business
    ).filter(
        db_models.Business.owner_id == current_user.id
    )
    
    if business_id:
        business = db.query(db_models.Business).filter(
            db_models.Business.id == business_id,
            db_models.Business.owner_id == current_user.id
        ).first()
        if not business:
            raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce business")
        query = query.filter(db_models.Expense.business_id == business_id)
    
    return query.all()