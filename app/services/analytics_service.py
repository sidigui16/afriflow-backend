
# AFRIFLOW/backend/app/services/analytics_service.py : le service d'analytics

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, case
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from app.models import models
import calendar

class AnalyticsService:
    """Service centralisé pour toutes les analytics"""
    
    def __init__(self, db: Session, business_id: int, user_id: int):
        self.db = db
        self.business_id = business_id
        self.user_id = user_id
        self._verify_access()
    
    def _verify_access(self):
        """Vérifie que l'utilisateur a accès à ce business"""
        business = self.db.query(models.Business).filter(
            models.Business.id == self.business_id,
            models.Business.owner_id == self.user_id
        ).first()
        if not business:
            raise ValueError("Accès non autorisé à ce business")
        return business
    
    def get_monthly_revenue(self, year: Optional[int] = None) -> List[Dict]:
        """Revenus mensuels avec noms des mois"""
        query = self.db.query(
            extract('month', models.Transaction.created_at).label('month'),
            func.sum(models.Transaction.amount).label('total'),
            func.count(models.Transaction.id).label('count')
        ).filter(
            models.Transaction.business_id == self.business_id
        )
        
        if year:
            query = query.filter(extract('year', models.Transaction.created_at) == year)
        
        results = query.group_by('month').order_by('month').all()
        
        # Ajouter les noms des mois
        months_fr = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        
        return [
            {
                "month_num": int(r[0]),
                "month_name": months_fr[int(r[0]) - 1],
                "total": float(r[1]),
                "transaction_count": r[2]
            }
            for r in results
        ]
    
    def get_expenses_by_category(self) -> List[Dict]:
        """Dépenses groupées par catégorie avec pourcentages"""
        total_expenses = self.db.query(
            func.sum(models.Expense.amount)
        ).filter(
            models.Expense.business_id == self.business_id
        ).scalar() or 0
        
        results = self.db.query(
            models.Expense.category,
            func.sum(models.Expense.amount).label('total'),
            func.count(models.Expense.id).label('count')
        ).filter(
            models.Expense.business_id == self.business_id
        ).group_by(models.Expense.category).order_by(func.sum(models.Expense.amount).desc()).all()
        
        return [
            {
                "category": r[0],
                "total": float(r[1]),
                "count": r[2],
                "percentage": round((float(r[1]) / total_expenses * 100), 2) if total_expenses > 0 else 0
            }
            for r in results
        ]
    
    def get_payment_methods_distribution(self) -> List[Dict]:
        """Distribution des méthodes de paiement"""
        total_transactions = self.db.query(
            func.sum(models.Transaction.amount)
        ).filter(
            models.Transaction.business_id == self.business_id
        ).scalar() or 0
        
        results = self.db.query(
            models.Transaction.payment_method,
            func.sum(models.Transaction.amount).label('total'),
            func.count(models.Transaction.id).label('count')
        ).filter(
            models.Transaction.business_id == self.business_id
        ).group_by(models.Transaction.payment_method).all()
        
        # Mapping des noms
        method_names = {
            "cash": "Espèces",
            "mobile_money": "Mobile Money",
            "card": "Carte bancaire",
            "bank_transfer": "Virement"
        }
        
        return [
            {
                "method": r[0],
                "method_name": method_names.get(r[0], r[0]),
                "total": float(r[1]),
                "count": r[2],
                "percentage": round((float(r[1]) / total_transactions * 100), 2) if total_transactions > 0 else 0
            }
            for r in results
        ]
    
    def get_top_categories(self, limit: int = 5) -> Dict[str, List]:
        """Top catégories de ventes et dépenses"""
        # Top ventes par catégorie
        top_sales = self.db.query(
            models.Transaction.category,
            func.sum(models.Transaction.amount).label('total'),
            func.count(models.Transaction.id).label('count')
        ).filter(
            models.Transaction.business_id == self.business_id
        ).group_by(models.Transaction.category).order_by(
            func.sum(models.Transaction.amount).desc()
        ).limit(limit).all()
        
        # Top dépenses par catégorie
        top_expenses = self.db.query(
            models.Expense.category,
            func.sum(models.Expense.amount).label('total'),
            func.count(models.Expense.id).label('count')
        ).filter(
            models.Expense.business_id == self.business_id
        ).group_by(models.Expense.category).order_by(
            func.sum(models.Expense.amount).desc()
        ).limit(limit).all()
        
        return {
            "top_sales_categories": [
                {
                    "category": r[0],
                    "total": float(r[1]),
                    "count": r[2]
                }
                for r in top_sales
            ],
            "top_expense_categories": [
                {
                    "category": r[0],
                    "total": float(r[1]),
                    "count": r[2]
                }
                for r in top_expenses
            ]
        }
    
    def get_daily_stats(self, days: int = 30) -> Dict:
        """Statistiques journalières pour les graphiques"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Requête pour les transactions quotidiennes
        daily_transactions = self.db.query(
            func.date(models.Transaction.created_at).label('date'),
            func.sum(models.Transaction.amount).label('revenue'),
            func.count(models.Transaction.id).label('transactions')
        ).filter(
            models.Transaction.business_id == self.business_id,
            func.date(models.Transaction.created_at) >= start_date
        ).group_by(func.date(models.Transaction.created_at)).all()
        
        # Requête pour les dépenses quotidiennes
        daily_expenses = self.db.query(
            func.date(models.Expense.created_at).label('date'),
            func.sum(models.Expense.amount).label('expenses'),
            func.count(models.Expense.id).label('expense_count')
        ).filter(
            models.Expense.business_id == self.business_id,
            func.date(models.Expense.created_at) >= start_date
        ).group_by(func.date(models.Expense.created_at)).all()
        
        # Créer un dictionnaire pour faciliter le merging
        data_by_date = {}
        
        for t in daily_transactions:
            # Vérifier le type de t[0] et le convertir en string si nécessaire
            if hasattr(t[0], 'isoformat'):
                date_str = t[0].isoformat()
            else:
                date_str = str(t[0])
            
            data_by_date[date_str] = {
                "date": date_str,
                "revenue": float(t[1]),
                "transactions": t[2],
                "expenses": 0,
                "expense_count": 0,
                "profit": float(t[1])
            }
        
        for e in daily_expenses:
            # Vérifier le type de e[0] et le convertir en string si nécessaire
            if hasattr(e[0], 'isoformat'):
                date_str = e[0].isoformat()
            else:
                date_str = str(e[0])
            
            if date_str in data_by_date:
                data_by_date[date_str]["expenses"] = float(e[1])
                data_by_date[date_str]["expense_count"] = e[2]
                data_by_date[date_str]["profit"] = data_by_date[date_str]["revenue"] - float(e[1])
            else:
                data_by_date[date_str] = {
                    "date": date_str,
                    "revenue": 0,
                    "transactions": 0,
                    "expenses": float(e[1]),
                    "expense_count": e[2],
                    "profit": -float(e[1])
                }
        
        # Trier par date
        result = sorted(data_by_date.values(), key=lambda x: x["date"])
        
        return {
            "daily_data": result,
            "summary": self._calculate_summary(result)
        }
    
    def _calculate_summary(self, daily_data: List[Dict]) -> Dict:
        """Calcule un résumé des statistiques"""
        total_revenue = sum(d["revenue"] for d in daily_data)
        total_expenses = sum(d["expenses"] for d in daily_data)
        total_profit = total_revenue - total_expenses
        avg_daily_revenue = total_revenue / len(daily_data) if daily_data else 0
        
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "total_profit": total_profit,
            "profit_margin": round((total_profit / total_revenue * 100), 2) if total_revenue > 0 else 0,
            "avg_daily_revenue": round(avg_daily_revenue, 2),
            "days_count": len(daily_data)
        }
    
    def get_comparative_stats(self, year: int) -> Dict:
        """Statistiques comparatives année précédente"""
        current_year_data = self.get_monthly_revenue(year)
        previous_year_data = self.get_monthly_revenue(year - 1)
        
        growth = []
        for i, current in enumerate(current_year_data):
            prev_total = next((p["total"] for p in previous_year_data if p["month_num"] == current["month_num"]), 0)
            growth_rate = ((current["total"] - prev_total) / prev_total * 100) if prev_total > 0 else 0
            growth.append({
                "month": current["month_name"],
                "current_year": current["total"],
                "previous_year": prev_total,
                "growth_rate": round(growth_rate, 2)
            })
        
        # Remplir les mois manquants de l'année précédente
        months_fr = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        
        for month_num, month_name in enumerate(months_fr, 1):
            if not any(g["month"] == month_name for g in growth):
                prev_total = next((p["total"] for p in previous_year_data if p["month_num"] == month_num), 0)
                growth.append({
                    "month": month_name,
                    "current_year": 0,
                    "previous_year": prev_total,
                    "growth_rate": -100 if prev_total > 0 else 0
                })
        
        # Trier par mois
        growth.sort(key=lambda x: months_fr.index(x["month"]))
        
        total_growth = sum(g["growth_rate"] for g in growth if g["growth_rate"] != -100)
        months_with_data = len([g for g in growth if g["growth_rate"] != -100])
        
        return {
            "year": year,
            "previous_year": year - 1,
            "monthly_comparison": growth,
            "year_over_year_growth": round(total_growth / months_with_data, 2) if months_with_data > 0 else 0
        }
    
    def get_cash_flow_analysis(self) -> Dict:
        """Analyse avancée du cash flow"""
        # Cash flow mensuel
        monthly_cash_flow = self.db.query(
            extract('month', models.Transaction.created_at).label('month'),
            extract('year', models.Transaction.created_at).label('year'),
            func.sum(case(
                (models.Transaction.payment_method == 'cash', models.Transaction.amount),
                else_=0
            )).label('cash'),
            func.sum(case(
                (models.Transaction.payment_method == 'mobile_money', models.Transaction.amount),
                else_=0
            )).label('mobile_money'),
            func.sum(case(
                (models.Transaction.payment_method == 'card', models.Transaction.amount),
                else_=0
            )).label('card'),
            func.sum(case(
                (models.Transaction.payment_method == 'bank_transfer', models.Transaction.amount),
                else_=0
            )).label('bank_transfer'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.business_id == self.business_id
        ).group_by(
            extract('year', models.Transaction.created_at),
            extract('month', models.Transaction.created_at)
        ).order_by('year', 'month').all()
        
        return {
            "monthly_breakdown": [
                {
                    "period": f"{int(r[1])}-{int(r[0]):02d}",
                    "cash": float(r[2] or 0),
                    "mobile_money": float(r[3] or 0),
                    "card": float(r[4] or 0),
                    "bank_transfer": float(r[5] or 0),
                    "total": float(r[6] or 0)
                }
                for r in monthly_cash_flow
            ]
        }
    
    def get_summary_stats(self) -> Dict:
        """Résumé des statistiques clés"""
        # Total revenus
        total_revenue = self.db.query(
            func.sum(models.Transaction.amount)
        ).filter(
            models.Transaction.business_id == self.business_id
        ).scalar() or 0
        
        # Total dépenses
        total_expenses = self.db.query(
            func.sum(models.Expense.amount)
        ).filter(
            models.Expense.business_id == self.business_id
        ).scalar() or 0
        
        # Nombre de transactions
        transaction_count = self.db.query(
            func.count(models.Transaction.id)
        ).filter(
            models.Transaction.business_id == self.business_id
        ).scalar() or 0
        
        # Nombre de dépenses
        expense_count = self.db.query(
            func.count(models.Expense.id)
        ).filter(
            models.Expense.business_id == self.business_id
        ).scalar() or 0
        
        # Transaction moyenne
        avg_transaction = total_revenue / transaction_count if transaction_count > 0 else 0
        
        # Dépense moyenne
        avg_expense = total_expenses / expense_count if expense_count > 0 else 0
        
        # Méthode de paiement principale
        top_payment_method = self.db.query(
            models.Transaction.payment_method,
            func.count(models.Transaction.id).label('count')
        ).filter(
            models.Transaction.business_id == self.business_id
        ).group_by(models.Transaction.payment_method).order_by(
            func.count(models.Transaction.id).desc()
        ).first()
        
        method_names = {
            "cash": "Espèces",
            "mobile_money": "Mobile Money",
            "card": "Carte bancaire",
            "bank_transfer": "Virement"
        }
        
        return {
            "totals": {
                "revenue": float(total_revenue),
                "expenses": float(total_expenses),
                "profit": float(total_revenue - total_expenses),
                "profit_margin": round(((total_revenue - total_expenses) / total_revenue * 100), 2) if total_revenue > 0 else 0
            },
            "counts": {
                "transactions": transaction_count,
                "expenses": expense_count
            },
            "averages": {
                "transaction": round(avg_transaction, 2),
                "expense": round(avg_expense, 2)
            },
            "top_payment_method": {
                "method": top_payment_method[0] if top_payment_method else None,
                "method_name": method_names.get(top_payment_method[0], top_payment_method[0]) if top_payment_method else None,
                "count": top_payment_method[1] if top_payment_method else 0
            } if top_payment_method else None
        }