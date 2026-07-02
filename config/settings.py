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
    WAIT_ROUNDS_AFTER_WIN = int(os.getenv("WAIT_ROUNDS_AFTER_WIN", 2))   # pausa após green normal
    WAIT_ROUNDS_AFTER_ZERO = int(os.getenv("WAIT_ROUNDS_AFTER_ZERO", 5))  # pausa quando o green é no 0
    # Pausa de análise quando o CRUPIÊ TROCA (lê o "movimento" do novo dealer
    # antes de voltar a entrar). Não muda a aleatoriedade da roda — é disciplina.
    WAIT_ROUNDS_AFTER_DEALER_CHANGE = int(os.getenv("WAIT_ROUNDS_AFTER_DEALER_CHANGE", 5))

    # Bloqueio de Números Base (User Request) — blacklist revisada em 2026-07-01.
    # Gatilhos ativos (permitidos): 2,4,5,6,12,13,14,16,18,19,20,21,22,23,24,25,26,29,34,35
    FORBIDDEN_NUMBERS = [7, 8, 9, 10, 11, 15, 17, 27, 28, 30, 33]

    # SPRINT 2 — Validação de estratégia real (feedback loop por winrate).
    STRATEGY_MIN_WINRATE = float(os.getenv("STRATEGY_MIN_WINRATE", 0.60))  # fração 0-1
    STRATEGY_MIN_SAMPLES = int(os.getenv("STRATEGY_MIN_SAMPLES", 30))

    # SPRINT 4 — RAG semântico real via embeddings Ollama (com fallback heurístico).
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
    RAG_EMBEDDING_HOST = os.getenv("RAG_EMBEDDING_HOST", "http://localhost:11434")
    RAG_EMBEDDING_TIMEOUT = float(os.getenv("RAG_EMBEDDING_TIMEOUT", 5.0))

    # SPRINT 5 — teto prático de posições na ficha de aposta do cassino (só aviso, não trunca).
    MAX_BET_SLOTS = int(os.getenv("MAX_BET_SLOTS", 20))

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

    # Captura de frames BRUTOS do WebSocket Playtech (ptielive) em
    # logs/ptielive_frames.jsonl — input exato consumido por
    # tools/pb_correlate.py para cravar o campo do número sorteado.
    # Ligado por padrão; só grava para URLs que contenham "ptielive".
    CAPTURE_PTIELIVE_FRAMES = (
        os.getenv("CAPTURE_PTIELIVE_FRAMES", "True").lower() == "true"
    )
    PTIELIVE_FRAMES_FILE = LOGS_DIR / "ptielive_frames.jsonl"

    # --- Detecção HÍBRIDA do número (protobuf primário + DOM fallback) ---
    # Quando ligado, o número é extraído direto do stream protobuf do gateway
    # ielive (mais rápido e preciso — sem leitura dupla do DOM). O
    # MutationObserver continua como FALLBACK automático: se o protobuf ficar
    # em silêncio (protocolo mudou/quebrou), o DOM reassume sozinho.
    PROTOBUF_PRIMARY = (
        os.getenv("PROTOBUF_PRIMARY", "True").lower() == "true"
    )
    # Janela (s) após uma entrega do protobuf na qual o número do DOM é
    # considerado redundante e descartado. Cobre o atraso de render do DOM
    # (~1-3s) e fica bem abaixo do intervalo entre rodadas (~30-60s).
    PROTOBUF_HEALTHY_WINDOW = float(os.getenv("PROTOBUF_HEALTHY_WINDOW", "12"))

    @classmethod
    def ensure_dirs(cls):
        """Ensure necessary directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Ensure directories exist on import
Settings.ensure_dirs()
