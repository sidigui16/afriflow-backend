# AFRIFLOW/backend/app/schemas/schemas.py

from pydantic import BaseModel, ConfigDict, field_serializer  # 👈 Ajout de field_serializer
from typing import Optional, List
from datetime import datetime

# ---------- USER SCHEMAS ----------
class UserCreate(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    
    model_config = ConfigDict(from_attributes=True)

# ---------- TOKEN SCHEMA ----------
class Token(BaseModel):
    access_token: str
    token_type: str

# ---------- BUSINESS SCHEMAS ----------
class BusinessCreate(BaseModel):
    name: str
    sector: Optional[str] = None
    currency: Optional[str] = "FCFA"

class BusinessOut(BaseModel):
    id: int
    name: str
    sector: Optional[str] = None
    currency: str
    owner_id: int
    
    model_config = ConfigDict(from_attributes=True)

class BusinessWithDetails(BusinessOut):
    transactions_count: Optional[int] = 0
    expenses_count: Optional[int] = 0
    total_revenue: Optional[float] = 0
    total_expenses: Optional[float] = 0
    
    model_config = ConfigDict(from_attributes=True)

# ---------- TRANSACTION SCHEMAS ----------
class TransactionCreate(BaseModel):
    amount: float
    payment_method: str
    category: str
    description: Optional[str] = ""
    business_id: int

class TransactionOut(BaseModel):
    id: int
    amount: float
    payment_method: str
    category: str
    description: Optional[str] = ""
    created_at: datetime
    business_id: int
    
    model_config = ConfigDict(from_attributes=True)  # 👈 Plus de json_encoders ici

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Sérialise un datetime en chaîne ISO 8601 pour JSON."""
        return value.isoformat()

# ---------- EXPENSE SCHEMAS ----------
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = ""
    business_id: int

class ExpenseOut(BaseModel):
    id: int
    amount: float
    category: str
    description: Optional[str] = ""
    created_at: datetime
    business_id: int
    
    model_config = ConfigDict(from_attributes=True)  # 👈 Plus de json_encoders ici

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Sérialise un datetime en chaîne ISO 8601 pour JSON."""
        return value.isoformat()

# ---------- ANALYTICS SCHEMAS ----------
class MonthlyRevenue(BaseModel):
    month_num: int
    month_name: str
    total: float
    transaction_count: int
    
    model_config = ConfigDict(from_attributes=True)

class ExpenseCategory(BaseModel):
    category: str
    total: float
    count: int
    percentage: float
    
    model_config = ConfigDict(from_attributes=True)

class PaymentMethod(BaseModel):
    method: str
    method_name: str
    total: float
    count: int
    percentage: float
    
    model_config = ConfigDict(from_attributes=True)

class TopCategory(BaseModel):
    category: str
    total: float
    count: int
    
    model_config = ConfigDict(from_attributes=True)

class DailyStat(BaseModel):
    date: str
    revenue: float
    transactions: int
    expenses: float
    expense_count: int
    profit: float
    
    model_config = ConfigDict(from_attributes=True)

class DailyStatsResponse(BaseModel):
    daily_data: List[DailyStat]
    summary: dict
    
    model_config = ConfigDict(from_attributes=True)

class ComparativeMonth(BaseModel):
    month: str
    current_year: float
    previous_year: float
    growth_rate: float
    
    model_config = ConfigDict(from_attributes=True)

class ComparativeStats(BaseModel):
    year: int
    previous_year: int
    monthly_comparison: List[ComparativeMonth]
    year_over_year_growth: float
    
    model_config = ConfigDict(from_attributes=True)

class CashFlowMonth(BaseModel):
    period: str
    cash: float
    mobile_money: float
    total: float
    
    model_config = ConfigDict(from_attributes=True)

class CashFlowAnalysis(BaseModel):
    monthly_breakdown: List[CashFlowMonth]
    
    model_config = ConfigDict(from_attributes=True)

class CompleteDashboard(BaseModel):
    business_info: dict
    monthly_revenue: List[MonthlyRevenue]
    expenses_by_category: List[ExpenseCategory]
    payment_methods: List[PaymentMethod]
    top_categories: dict
    daily_stats: DailyStatsResponse
    cash_flow: CashFlowAnalysis
    
    model_config = ConfigDict(from_attributes=True)