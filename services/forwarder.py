from telegram.ext import ApplicationBuilder, MessageHandler, filters
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ✅ IDs confirmados
GRUPO_ORIGEM_ID = 8498989415
GRUPO_DESTINO_ID = -1002800575942

PALAVRAS_CHAVE = [
    "ENTRADA CONFIRMADA",
    "TWINS",
    "FAMÍLIA",
    "ROULETA",
]

async def escutar_e_forward(update, context):
    msg = update.effective_message

    if msg.chat_id != GRUPO_ORIGEM_ID:
        return

    texto = msg.text or msg.caption or ""
    texto_upper = texto.upper()

    # se quiser forwardar TUDO, é só remover este IF
    if not any(p in texto_upper for p in PALAVRAS_CHAVE):
        return

    await context.bot.forward_message(
        chat_id=GRUPO_DESTINO_ID,
        from_chat_id=GRUPO_ORIGEM_ID,
        message_id=msg.message_id
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, escutar_e_forward))

    print("🔁 Forward automático Grupo → Grupo ATIVO")
    app.run_polling()

if __name__ == "__main__":
    main()
