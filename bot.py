import os
import csv
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Estados da conversa
VALOR, CATEGORIA, DESCRICAO = range(3)

# Configurações para a nuvem (o Render fornece a porta automaticamente)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "9075809027:AAG-IJgDq25kqzf-xILyITTbnSfHu1f7GO8")
PORT = int(os.environ.get("PORT", 10000))

# ⚠️ MUDE AQUI: Cole o URL exato que o Render te deu (ex: https://controle-gastos-eper.onrender.com)
RENDER_URL = "https://controle-gastos-eper.onrender.com"

ARQUIVO_CSV = "gastos.csv"


async def iniciar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "💰 Qual foi o **valor** do gasto? (Digite apenas o número, ex: 35.50)"
    )
    return VALOR


async def receber_valor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.replace(",", ".").strip()

    try:
        valor = float(texto)
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Digite apenas números (ex: 42.90):")
        return VALOR

    context.user_data["valor"] = valor

    teclado = [
        [InlineKeyboardButton("🚗 Transporte", callback_data="Transporte")],
        [InlineKeyboardButton("🍔 Alimentação", callback_data="Alimentação")],
        [InlineKeyboardButton("🎉 Lazer", callback_data="Lazer")],
    ]
    reply_markup = InlineKeyboardMarkup(teclado)

    await update.message.reply_text(
        f"Valor registrado: **R$ {valor:.2f}**\nAgora selecione a **categoria**:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return CATEGORIA


async def receber_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    categoria = query.data
    context.user_data["categoria"] = categoria

    await query.edit_message_text(
        text=(
            f"🏷️ Categoria selecionada: **{categoria}**\n\n"
            "📝 **Quer descrever melhor seu gasto?**\n"
            "Escreva a descrição abaixo:"
        ),
        parse_mode="Markdown",
    )
    return DESCRICAO


async def receber_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descricao = update.message.text.strip()
    valor = context.user_data["valor"]
    categoria = context.user_data["categoria"]
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Salva no arquivo CSV
    with open(ARQUIVO_CSV, mode="a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow([data_hora, f"{valor:.2f}", categoria, descricao])

    await update.message.reply_text(
        text=(
            f"✅ **Gasto salvo com sucesso!**\n\n"
            f"📅 Data: {data_hora}\n"
            f"💵 Valor: R$ {valor:.2f}\n"
            f"🏷️ Categoria: {categoria}\n"
            f"💬 Descrição: {descricao}\n\n"
            f"Envie /gasto para registrar outro."
        ),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registro cancelado.")
    return ConversationHandler.END


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", iniciar_gasto)],
        states={
            VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_valor)],
            CATEGORIA: [CallbackQueryHandler(receber_categoria)],
            DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_descricao)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)

    print(f"Iniciando bot via Webhook na porta {PORT}...")
    
    # Abre a porta web que o Render exige
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{RENDER_URL}/{TOKEN}"
    )


if __name__ == "__main__":
    main()
