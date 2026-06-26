import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the single root '.env'
env_path_root = BASE_DIR / ".env"

if env_path_root.exists():
    load_dotenv(dotenv_path=env_path_root)
else:
    load_dotenv()


class Settings:
    # Telegram Configuration
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Game Configuration
    GAME_URL = os.getenv("GAME_URL")
    API_URL = os.getenv("API_URL")
    API_KEY = os.getenv("API_KEY")
    BET_AMOUNT = float(os.getenv("BET_AMOUNT", 10.0))
    WAIT_ROUNDS_AFTER_WIN = int(os.getenv("WAIT_ROUNDS_AFTER_WIN", 1))
    WAIT_ROUNDS_AFTER_ZERO = int(os.getenv("WAIT_ROUNDS_AFTER_ZERO", 5))

    # Bloqueio de Números Base (User Request)
    # Reativados em {{DATA}}: 0, 5, 8, 10
    FORBIDDEN_NUMBERS = [7, 9, 11, 17, 22, 27, 33]

    # Estatísticas e Turbulência
    STATS_WINDOW_SIZE = 60
    TURBULENCE_TH_SIGMA = 3.0  # Threshold para TURBULÊNCIA EXTREMA (bloqueio)
    STABILITY_TH_SIGMA = 2.0  # Threshold relaxado para volta à operação
    EXTREME_TURBULENCE_CATEGORIES = 2  # Categorias simultâneas para considerar EXTREMA

    # Integridade Windows 10
    MIN_SPIN_TIME = 15.0  # Segundos mínimos físicos de um giro normal
    MIN_BATCH_DELTA = 0.2  # Delay sintético para batch delivery (Windows)
    MAX_REPETITIONS_FOR_INVALID = 3  # Limite de repetições em batch

    # Fallback Operacional
    MAX_INACTIVITY_SPINS = (
        20  # Se ficar 20 giros sem sinal, ignora filtros não-críticos
    )

    # Path Configuration
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    BROWSER_PROFILE_DIR = BASE_DIR / "playwright_profile"
    DB_PATH = DATA_DIR / "database.sqlite"
    LOG_FILE = LOGS_DIR / "bot.log"

    # Playwright Configuration
    HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

    @classmethod
    def ensure_dirs(cls):
        """Ensure necessary directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Ensure directories exist on import
Settings.ensure_dirs()
