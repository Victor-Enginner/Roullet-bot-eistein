import os
import shutil
import time
import threading
from datetime import datetime
from config.settings import Settings
from utils.logger import setup_logger

logger = setup_logger('backup')

class BackupSystem:
    """
    Sistema de backup automático para o banco de dados roulette.db.
    Executa em uma thread separada para não bloquear o bot.
    """
    def __init__(self, db_path=None, backup_dir=None, interval_hours=24):
        self.db_path = db_path or str(Settings.DB_PATH)
        self.backup_dir = backup_dir or str(Settings.DATA_DIR / 'backups')
        self.interval_seconds = interval_hours * 3600
        self.running = False
        self._thread = None
        
        # Garante que o diretório de backup existe
        os.makedirs(self.backup_dir, exist_ok=True)
        logger.info(f"BackupSystem inicializado. Intervalo: {interval_hours}h")

    def start(self):
        """Inicia a thread de backup"""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Thread de backup iniciada.")

    def stop(self):
        """Para a thread de backup"""
        self.running = False
        logger.info("BackupSystem parando...")

    def _run_loop(self):
        """Loop principal do backup"""
        # Faz um backup inicial imediato se o arquivo existir
        self.do_backup()
        
        while self.running:
            time.sleep(60) # Verifica a cada minuto se deve parar ou continuar esperando
            
            # Cálculo simplificado para esperar o intervalo
            # Para evitar sleep longo que impede o stop() imediato
            last_run = getattr(self, '_last_run', 0)
            if time.time() - last_run >= self.interval_seconds:
                self.do_backup()

    def do_backup(self):
        """Executa a cópia física do arquivo"""
        if not os.path.exists(self.db_path):
            logger.warning(f"Arquivo de banco de dados não encontrado para backup: {self.db_path}")
            return False

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(self.db_path)
            backup_name = f"{os.path.splitext(filename)[0]}_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            shutil.copy2(self.db_path, backup_path)
            self._last_run = time.time()
            
            logger.info(f"✅ Backup realizado com sucesso: {backup_name}")
            self._cleanup_old_backups()
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao realizar backup: {e}", exc_info=True)
            return False

    def _cleanup_old_backups(self, keep_last=7):
        """Remove backups antigos para economizar espaço"""
        try:
            backups = [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.endswith('.db')]
            backups.sort(key=os.path.getmtime, reverse=True)
            
            if len(backups) > keep_last:
                for old_backup in backups[keep_last:]:
                    os.remove(old_backup)
                    logger.debug(f"Removendo backup antigo: {os.path.basename(old_backup)}")
        except Exception as e:
            logger.error(f"Erro ao limpar backups: {e}")

# Instância Singleton opcional
backup_system = BackupSystem()
