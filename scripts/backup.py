
# Afriflow/backend/scripts/backup.py - Sauvegarde automatique des données

#!/usr/bin/env python3
"""
Script de sauvegarde automatique pour Afriflow
Gère: backup DB, upload cloud, rotation, alertes
Version: 2.0.0
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
import gzip
import shutil
import boto3
from pathlib import Path
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import DATABASE_URL, BACKUP_CONFIG, SMTP_CONFIG

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/data/logs/backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AfriflowBackup:
    """Gestionnaire de sauvegardes"""
    
    def __init__(self):
        self.backup_dir = Path('/data/backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration cloud (optionnel)
        self.s3_client = None
        if os.getenv('AWS_ACCESS_KEY_ID'):
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'eu-west-3')
            )
        
        self.retention_days = BACKUP_CONFIG.get('retention_days', 30)
        self.backup_time = datetime.now()
    
    def run(self):
        """Exécute la sauvegarde complète"""
        logger.info("🚀 Démarrage de la sauvegarde Afriflow")
        
        try:
            # 1. Backup base de données
            db_backup_path = self.backup_database()
            
            # 2. Backup fichiers uploadés
            files_backup_path = self.backup_files()
            
            # 3. Backup configuration
            config_backup_path = self.backup_config()
            
            # 4. Upload vers cloud (si configuré)
            if self.s3_client:
                self.upload_to_cloud(db_backup_path)
                self.upload_to_cloud(files_backup_path)
                self.upload_to_cloud(config_backup_path)
            
            # 5. Nettoyage vieux backups
            self.cleanup_old_backups()
            
            # 6. Envoyer notification
            self.send_notification(success=True)
            
            logger.info("✅ Sauvegarde terminée avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            self.send_notification(success=False, error=str(e))
            sys.exit(1)
    
    def backup_database(self) -> Path:
        """Sauvegarde la base de données PostgreSQL"""
        logger.info("💾 Backup base de données...")
        
        # Extraire les infos de connexion
        # DATABASE_URL = postgresql://user:pass@host:port/dbname
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
        
        if not match:
            raise ValueError("Format DATABASE_URL invalide")
        
        user, password, host, port, dbname = match.groups()
        
        # Nom du fichier
        timestamp = self.backup_time.strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"
        compressed_file = backup_file.with_suffix('.sql.gz')
        
        # Commande pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-F', 'c',  # Format custom (compressé)
            '-f', str(backup_file)
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        # Compresser
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Supprimer le fichier non compressé
        backup_file.unlink()
        
        logger.info(f"✅ Base sauvegardée: {compressed_file} ({compressed_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return compressed_file
    
    def backup_files(self) -> Path:
        """Sauvegarde les fichiers uploadés"""
        logger.info("📁 Backup fichiers...")
        
        upload_dirs = ['/data/invoices', '/data/reports', '/data/logs']
        timestamp = self.backup_time.strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"files_backup_{timestamp}.tar.gz"
        
        # Créer archive
        files_to_backup = []
        for directory in upload_dirs:
            if Path(directory).exists():
                files_to_backup.extend(Path(directory).glob('*'))
        
        if not files_to_backup:
            logger.info("Aucun fichier à sauvegarder")
            return None
        
        import tarfile
        with tarfile.open(backup_file, 'w:gz') as tar:
            for file_path in files_to_backup:
                tar.add(file_path, arcname=file_path.name)
        
        logger.info(f"✅ Fichiers sauvegardés: {backup_file} ({backup_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return backup_file
    
    def backup_config(self) -> Path:
        """Sauvegarde la configuration"""
        logger.info("⚙️ Backup configuration...")
        
        timestamp = self.backup_time.strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"config_backup_{timestamp}.yaml"
        
        config = {
            'timestamp': self.backup_time.isoformat(),
            'environment': os.getenv('ENVIRONMENT', 'production'),
            'database': {
                'host': os.getenv('DB_HOST', 'localhost'),
                'name': os.getenv('DB_NAME', 'afriflow'),
            },
            'features': {
                'payments': bool(os.getenv('ORANGE_MONEY_API_KEY')),
                'sms': bool(os.getenv('TWILIO_ACCOUNT_SID')),
                'email': bool(os.getenv('SMTP_HOST')),
            },
            'backup': {
                'retention_days': self.retention_days,
                'last_backup': self.backup_time.isoformat()
            }
        }
        
        with open(backup_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"✅ Configuration sauvegardée: {backup_file}")
        return backup_file
    
    def upload_to_cloud(self, file_path: Path):
        """Upload vers S3 (ou autre cloud)"""
        if not file_path or not file_path.exists():
            return
        
        logger.info(f"☁️ Upload vers cloud: {file_path.name}")
        
        bucket = os.getenv('AWS_BUCKET_NAME', 'afriflow-backups')
        key = f"backups/{self.backup_time.strftime('%Y/%m/%d')}/{file_path.name}"
        
        self.s3_client.upload_file(
            str(file_path),
            bucket,
            key,
            ExtraArgs={'StorageClass': 'STANDARD_IA'}  # Stockage froid (moins cher)
        )
        
        logger.info(f"✅ Uploadé vers s3://{bucket}/{key}")
    
    def cleanup_old_backups(self):
        """Supprime les vieux backups locaux"""
        logger.info("🧹 Nettoyage vieux backups...")
        
        cutoff = self.backup_time - timedelta(days=self.retention_days)
        deleted = 0
        
        for backup_file in self.backup_dir.glob('*_backup_*'):
            if backup_file.stat().st_mtime < cutoff.timestamp():
                backup_file.unlink()
                deleted += 1
        
        logger.info(f"✅ {deleted} vieux backups supprimés")
    
    def send_notification(self, success: bool, error: str = None):
        """Envoie notification par email"""
        if not SMTP_CONFIG.get('enabled'):
            return
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_CONFIG['from']
        msg['To'] = SMTP_CONFIG['admin_email']
        msg['Subject'] = f"[Afriflow] Backup {'✅ Succès' if success else '❌ Échec'}"
        
        if success:
            body = f"""
            <h2>Sauvegarde réussie ✅</h2>
            <p><strong>Date:</strong> {self.backup_time.strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Fichiers:</strong></p>
            <ul>
                <li>Base de données: db_backup_{self.backup_time.strftime('%Y%m%d_%H%M%S')}.sql.gz</li>
                <li>Fichiers: files_backup_{self.backup_time.strftime('%Y%m%d_%H%M%S')}.tar.gz</li>
                <li>Configuration: config_backup_{self.backup_time.strftime('%Y%m%d_%H%M%S')}.yaml</li>
            </ul>
            <p><strong>Taille totale:</strong> {self.get_backup_size():.2f} MB</p>
            """
        else:
            body = f"""
            <h2>Échec de la sauvegarde ❌</h2>
            <p><strong>Date:</strong> {self.backup_time.strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Erreur:</strong> {error}</p>
            <p>Veuillez vérifier les logs: /data/logs/backup.log</p>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.send_message(msg)
        
        logger.info("📧 Notification envoyée")
    
    def get_backup_size(self) -> float:
        """Calcule la taille totale des backups"""
        total = 0
        for backup_file in self.backup_dir.glob('*_backup_*'):
            total += backup_file.stat().st_size
        return total / 1024 / 1024

def main():
    """Point d'entrée principal"""
    backup = AfriflowBackup()
    backup.run()

if __name__ == "__main__":
    main()