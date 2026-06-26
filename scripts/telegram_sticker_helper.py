import argparse
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASE_DIR, Settings
from services.telegram_events import EVENT_STICKER_ENV, get_sticker_id, is_sticker_enabled
from services.bot import TelegramBot


def load_env():
    root_env = BASE_DIR / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)


def list_stickers():
    load_env()
    token = Settings.TELEGRAM_TOKEN
    if not token:
        raise SystemExit("TELEGRAM_TOKEN não configurado.")

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        raise SystemExit(f"Telegram retornou erro: {payload}")

    found = 0
    for update in payload.get("result", []):
        message = update.get("message") or update.get("channel_post") or {}
        sticker = message.get("sticker")
        if not sticker:
            continue

        found += 1
        chat = message.get("chat", {})
        print("=" * 80)
        print(f"chat_id: {chat.get('id')}")
        print(f"chat_title: {chat.get('title') or chat.get('username') or chat.get('first_name')}")
        print(f"emoji: {sticker.get('emoji')}")
        print(f"set_name: {sticker.get('set_name')}")
        print(f"file_unique_id: {sticker.get('file_unique_id')}")
        print(f"file_id: {sticker.get('file_id')}")

    if not found:
        print("Nenhum sticker encontrado nos updates recentes.")
        print("Envie um sticker no privado do bot ou no grupo onde ele está e rode de novo.")


def show_config():
    load_env()
    print(f"TELEGRAM_SEND_STICKERS ativo: {is_sticker_enabled()}")
    for event_key, env_name in EVENT_STICKER_ENV.items():
        print(f"{event_key:18} {env_name:36} configurado={bool(get_sticker_id(event_key))}")


def test_event(event_key: str):
    load_env()
    if event_key not in EVENT_STICKER_ENV:
        valid = ", ".join(EVENT_STICKER_ENV)
        raise SystemExit(f"Evento inválido: {event_key}. Use um destes: {valid}")

    bot = TelegramBot(Settings.TELEGRAM_TOKEN, Settings.TELEGRAM_CHAT_ID)
    msg = (
        f"🧪 TESTE DE EVENTO TELEGRAM\n\n"
        f"Evento: {event_key}\n"
        f"Sticker configurado: {bool(get_sticker_id(event_key))}"
    )
    ok = bot.enviar_evento(event_key, msg, imediato=True)
    print(f"Mensagem enviada: {ok}")


def main():
    parser = argparse.ArgumentParser(description="Ajuda a capturar e testar stickers do Telegram.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Lista file_id de stickers recebidos pelo bot.")
    sub.add_parser("config", help="Mostra quais eventos têm sticker configurado.")

    test_parser = sub.add_parser("test", help="Testa uma mensagem/sticker de evento.")
    test_parser.add_argument("event", choices=sorted(EVENT_STICKER_ENV.keys()))

    args = parser.parse_args()
    if args.command == "list":
        list_stickers()
    elif args.command == "config":
        show_config()
    elif args.command == "test":
        test_event(args.event)


if __name__ == "__main__":
    main()
