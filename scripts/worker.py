
# Afriflow/backend/scripts/worker.py - Gestionnaire de tâches asynchrones

#!/usr/bin/env python3
"""
Worker pour les tâches asynchrones d'Afriflow
Gère: envois d'emails, exports PDF, notifications, nettoyage
Version: 2.0.0
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import redis
from sqlalchemy import create_engine, text, extract, func  # 👈 AJOUT DE extract ICI
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd
import io
import aiohttp
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import models
from app.config import DATABASE_URL, REDIS_URL, SMTP_CONFIG

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/data/logs/worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AfriflowWorker:
    """Worker principal pour les tâches asynchrones"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL)
        self.db = SessionLocal()
        self.running = True
        self.task_handlers = {
            'send_email': self.handle_send_email,
            'export_report': self.handle_export_report,
            'notify_user': self.handle_notify_user,
            'cleanup_temp': self.handle_cleanup_temp,
            'process_payment': self.handle_process_payment,
            'generate_invoice': self.handle_generate_invoice,
            'backup_data': self.handle_backup_data,
            'send_sms': self.handle_send_sms,
        }
    
    async def run(self):
        """Boucle principale du worker"""
        logger.info("🚀 Worker Afriflow démarré")
        
        while self.running:
            try:
                # Récupérer une tâche de la queue Redis
                task_data = self.redis_client.blpop('afriflow:tasks', timeout=5)
                
                if task_data:
                    _, task_json = task_data
                    task = json.loads(task_json)
                    await self.process_task(task)
                
                # Nettoyage périodique
                await self.periodic_cleanup()
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                await asyncio.sleep(5)
        
        logger.info("🛑 Worker Afriflow arrêté")
    
    async def process_task(self, task: Dict[str, Any]):
        """Traite une tâche individuelle"""
        task_id = task.get('id')
        task_type = task.get('type')
        task_data = task.get('data', {})
        
        logger.info(f"📦 Traitement tâche {task_id}: {task_type}")
        
        try:
            handler = self.task_handlers.get(task_type)
            if handler:
                result = await handler(task_data)
                await self.mark_task_completed(task_id, result)
            else:
                logger.warning(f"Type de tâche inconnu: {task_type}")
                await self.mark_task_failed(task_id, "Type inconnu")
                
        except Exception as e:
            logger.error(f"❌ Erreur tâche {task_id}: {e}")
            await self.mark_task_failed(task_id, str(e))
    
    # ========== Gestionnaires de tâches ==========
    
    async def handle_send_email(self, data: Dict) -> Dict:
        """Envoi d'email"""
        to_email = data['to']
        subject = data['subject']
        content = data['content']
        attachments = data.get('attachments', [])
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_CONFIG['from']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'html' if data.get('html') else 'plain'))
        
        for attachment in attachments:
            with open(attachment['path'], 'rb') as f:
                part = MIMEApplication(f.read(), Name=attachment['name'])
                part['Content-Disposition'] = f'attachment; filename="{attachment["name"]}"'
                msg.attach(part)
        
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.send_message(msg)
        
        logger.info(f"📧 Email envoyé à {to_email}")
        return {"status": "sent", "to": to_email}
    
    async def handle_export_report(self, data: Dict) -> Dict:
        """Export de rapport en PDF/Excel"""
        business_id = data['business_id']
        report_type = data['type']  # 'monthly', 'annual', 'custom'
        format_type = data.get('format', 'pdf')  # Renommé 'format' en 'format_type'
        date_range = data.get('date_range', {})
        
        # Récupérer les données
        db = SessionLocal()
        
        try:
            if report_type == 'monthly':
                # Rapport mensuel
                transactions = db.query(models.Transaction).filter(
                    models.Transaction.business_id == business_id,
                    models.Transaction.created_at >= date_range['start'],
                    models.Transaction.created_at <= date_range['end']
                ).all()
                
                expenses = db.query(models.Expense).filter(
                    models.Expense.business_id == business_id,
                    models.Expense.created_at >= date_range['start'],
                    models.Expense.created_at <= date_range['end']
                ).all()
                
            elif report_type == 'annual':
                # Rapport annuel avec comparaisons
                current_year = datetime.now().year
                
                # ✅ Utilisation correcte de extract avec SQLAlchemy 2.0
                transactions = db.query(models.Transaction).filter(
                    models.Transaction.business_id == business_id,
                    extract('year', models.Transaction.created_at) == current_year
                ).all()
                
                expenses = db.query(models.Expense).filter(
                    models.Expense.business_id == business_id,
                    extract('year', models.Expense.created_at) == current_year
                ).all()
        finally:
            db.close()
        
        # Créer le rapport
        if format_type == 'excel':
            output = await self.create_excel_report(transactions, expenses, business_id)
        else:
            output = await self.create_pdf_report(transactions, expenses, business_id)
        
        # Sauvegarder
        report_path = f"/data/reports/report_{business_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        os.makedirs('/data/reports', exist_ok=True)
        
        with open(report_path, 'wb') as f:
            f.write(output)
        
        return {
            "status": "completed",
            "path": report_path,
            "transactions": len(transactions),
            "expenses": len(expenses)
        }
    
    async def handle_notify_user(self, data: Dict) -> Dict:
        """Notification utilisateur"""
        user_id = data['user_id']
        notification_type = data['notification_type']
        message = data['message']
        
        db = SessionLocal()
        try:
            # Sauvegarder dans la base
            notification = models.Notification(
                user_id=user_id,
                type=notification_type,
                message=message,
                read=False,
                created_at=datetime.utcnow()
            )
            
            db.add(notification)
            db.commit()
            
            # Si notification urgente, envoyer aussi par email
            if data.get('urgent', False):
                user = db.query(models.User).filter(models.User.id == user_id).first()
                if user:
                    await self.handle_send_email({
                        'to': user.email,
                        'subject': f"Afriflow - {notification_type}",
                        'content': message
                    })
        finally:
            db.close()
        
        return {"status": "notified", "user_id": user_id}
    
    async def handle_cleanup_temp(self, data: Dict) -> Dict:
        """Nettoyage des fichiers temporaires"""
        days_old = data.get('days_old', 7)
        cutoff = datetime.now() - timedelta(days=days_old)
        
        # Nettoyer les vieux rapports
        report_dir = Path('/data/reports')
        cleaned = 0
        if report_dir.exists():
            for file in report_dir.glob('*'):
                if file.stat().st_mtime < cutoff.timestamp():
                    file.unlink()
                    cleaned += 1
        
        # Nettoyer les vieux logs
        log_dir = Path('/data/logs')
        if log_dir.exists():
            for file in log_dir.glob('*.log'):
                if file.stat().st_mtime < cutoff.timestamp():
                    file.unlink()
                    cleaned += 1
        
        logger.info(f"🧹 Nettoyage: {cleaned} fichiers supprimés")
        return {"cleaned": cleaned}
    
    async def handle_process_payment(self, data: Dict) -> Dict:
        """Traitement des paiements asynchrones"""
        payment_id = data['payment_id']
        provider = data['provider']  # 'orange_money', 'mtn_money', etc.
        amount = data['amount']
        phone = data['phone']
        
        # Simuler appel API au fournisseur
        async with aiohttp.ClientSession() as session:
            if provider == 'orange_money':
                url = "https://api.orange.com/payment/v1/transaction"
                headers = {"Authorization": f"Bearer {os.getenv('ORANGE_MONEY_TOKEN')}"}
                payload = {
                    "amount": amount,
                    "phone": phone,
                    "reference": payment_id
                }
            elif provider == 'mtn_money':
                url = "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay"
                headers = {"X-Reference-Id": payment_id}
                payload = {
                    "amount": str(amount),
                    "currency": "XOF",
                    "externalId": payment_id,
                    "payer": {"partyIdType": "MSISDN", "partyId": phone},
                    "payerMessage": "Paiement Afriflow",
                    "payeeNote": "Merci pour votre paiement"
                }
            else:
                return {"status": "error", "message": f"Provider {provider} non supporté"}
            
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    result = await resp.json()
                    status = "success" if resp.status == 200 else "failed"
                    
                    # Mettre à jour la transaction dans la base
                    db = SessionLocal()
                    try:
                        payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
                        if payment:
                            payment.status = status
                            payment.provider_response = result
                            db.commit()
                    finally:
                        db.close()
                    
                    return {"status": status, "provider": provider, "response": result}
                    
            except Exception as e:
                logger.error(f"❌ Erreur paiement {provider}: {e}")
                return {"status": "error", "message": str(e)}
    
    async def handle_generate_invoice(self, data: Dict) -> Dict:
        """Génération de facture PDF"""
        business_id = data['business_id']
        transaction_ids = data['transaction_ids']
        
        db = SessionLocal()
        try:
            business = db.query(models.Business).filter(models.Business.id == business_id).first()
            transactions = db.query(models.Transaction).filter(
                models.Transaction.id.in_(transaction_ids)
            ).all()
            
            # Générer PDF avec reportlab
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # En-tête
            elements.append(Paragraph(f"Facture - {business.name}", styles['Title']))
            elements.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Tableau des transactions
            table_data = [['Date', 'Montant', 'Méthode', 'Catégorie']]
            total = 0
            for t in transactions:
                table_data.append([
                    t.created_at.strftime('%d/%m/%Y'),
                    f"{t.amount:,.0f} FCFA",
                    t.payment_method,
                    t.category
                ])
                total += t.amount
            
            table_data.append(['', f"Total: {total:,.0f} FCFA", '', ''])
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -2), 1, colors.black)
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            # Sauvegarder
            pdf_path = f"/data/invoices/invoice_{business_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            os.makedirs('/data/invoices', exist_ok=True)
            
            with open(pdf_path, 'wb') as f:
                f.write(buffer.getvalue())
            
        finally:
            db.close()
        
        return {"path": pdf_path, "transactions": len(transactions), "total": total}
    
    async def handle_backup_data(self, data: Dict) -> Dict:
        """Backup des données"""
        # Déclenché par le cron, voir backup.py
        logger.info("Tâche de backup déclenchée")
        return {"status": "triggered"}
    
    async def handle_send_sms(self, data: Dict) -> Dict:
        """Envoi de SMS (pour l'Afrique, essentiel!)"""
        phone = data['phone']
        message = data['message']
        
        # Vérifier que les variables Twilio sont configurées
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logger.error("Configuration Twilio manquante")
            return {"status": "error", "message": "Twilio non configuré"}
        
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            
            sms = client.messages.create(
                body=message,
                from_=from_number,
                to=phone
            )
            
            logger.info(f"📱 SMS envoyé à {phone}")
            return {"status": "sent", "sid": sms.sid}
        except Exception as e:
            logger.error(f"❌ Erreur envoi SMS: {e}")
            return {"status": "error", "message": str(e)}
    
    # ========== Utilitaires ==========
    
    async def create_excel_report(self, transactions, expenses, business_id):
        """Crée un rapport Excel"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet Transactions
            tx_data = [{
                'Date': t.created_at.strftime('%d/%m/%Y'),
                'Montant': t.amount,
                'Méthode': t.payment_method,
                'Catégorie': t.category,
                'Description': t.description or ''
            } for t in transactions]
            
            if tx_data:
                df_tx = pd.DataFrame(tx_data)
                df_tx.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Sheet Dépenses
            exp_data = [{
                'Date': e.created_at.strftime('%d/%m/%Y'),
                'Montant': e.amount,
                'Catégorie': e.category,
                'Description': e.description or ''
            } for e in expenses]
            
            if exp_data:
                df_exp = pd.DataFrame(exp_data)
                df_exp.to_excel(writer, sheet_name='Dépenses', index=False)
            
            # Sheet Résumé
            total_revenue = sum(t.amount for t in transactions)
            total_expenses = sum(e.amount for e in expenses)
            
            summary = {
                'Total Revenus': total_revenue,
                'Total Dépenses': total_expenses,
                'Profit Net': total_revenue - total_expenses,
                'Nb Transactions': len(transactions),
                'Nb Dépenses': len(expenses),
                'Période du': min((t.created_at for t in transactions), default=None).strftime('%d/%m/%Y') if transactions else None,
                'Période au': max((t.created_at for t in transactions), default=None).strftime('%d/%m/%Y') if transactions else None
            }
            
            df_summary = pd.DataFrame([summary])
            df_summary.to_excel(writer, sheet_name='Résumé', index=False)
        
        return output.getvalue()
    
    async def create_pdf_report(self, transactions, expenses, business_id):
        """Crée un rapport PDF"""
        # Pour l'instant, retourne un PDF simple
        # Idéalement, utiliser reportlab ou weasyprint
        return b"PDF report placeholder"
    
    async def mark_task_completed(self, task_id: str, result: Dict):
        """Marque une tâche comme terminée"""
        self.redis_client.setex(
            f"afriflow:task:result:{task_id}",
            3600,
            json.dumps({"status": "completed", "result": result})
        )
    
    async def mark_task_failed(self, task_id: str, error: str):
        """Marque une tâche comme échouée"""
        self.redis_client.setex(
            f"afriflow:task:result:{task_id}",
            3600,
            json.dumps({"status": "failed", "error": error})
        )
    
    async def periodic_cleanup(self):
        """Nettoyage périodique"""
        # Vérifier toutes les heures
        last_cleanup = self.redis_client.get('afriflow:last_cleanup')
        
        if not last_cleanup or (datetime.now().timestamp() - float(last_cleanup)) > 3600:
            await self.handle_cleanup_temp({"days_old": 7})
            self.redis_client.set('afriflow:last_cleanup', datetime.now().timestamp())

async def main():
    """Point d'entrée principal"""
    worker = AfriflowWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        worker.running = False
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())