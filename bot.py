import os
import csv
from datetime import datetime, timezone, timedelta
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

# Estados da conversa (adicionado QUEM no início)
QUEM, VALOR, CATEGORIA, DESCRICAO = range(4)

# Configurações do Bot e Render
TOKEN = os.environ.get("TELEGRAM_TOKEN", "9075809027:AAG-IJgDq25kqzf-xILyITTbnSfHu1f7GO8")
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://controle-gastos-eper.onrender.com"

ARQUIVO_CSV = "gastos.csv"

# Garante que o CSV nasce com o cabeçalho atualizado (incluindo "Quem")
if not os.path.exists(ARQUIVO_CSV):
    with open(ARQUIVO_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Gasto", "Valor", "Mês", "Dia", "Ano", "Categoria", "Descrição", "Quem"])


async def iniciar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    teclado = [
        [InlineKeyboardButton("🙋‍♂️ Fernando", callback_data="Fernando")],
        [InlineKeyboardButton("🙋‍♀️ Namorada", callback_data="Namorada")],
    ]
    reply_markup = InlineKeyboardMarkup(teclado)

    await update.message.reply_text(
        "👤 **Quem está a fazer este registo?**",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return QUEM


async def receber_quem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    quem = query.data
    context.user_data["quem"] = quem

    await query.edit_message_text(
        text=f"👤 Registado por: **{quem}**\n\n💰 Qual foi o **valor** do gasto? (Digite apenas o número, ex: 35.50)",
        parse_mode="Markdown",
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
        f"Valor: **R$ {valor:.2f}**\nAgora selecione a **categoria**:",
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
            f"🏷️ Categoria: **{categoria}**\n\n"
            "📝 **Qual foi o gasto / descrição?**\n"
            "Escreva abaixo (ex: Almoço, Uber):"
        ),
        parse_mode="Markdown",
    )
    return DESCRICAO


async def receber_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descricao = update.message.text.strip()
    valor = context.user_data["valor"]
    categoria = context.user_data["categoria"]
    quem = context.user_data["quem"]

    # Fuso horário de Brasília (UTC-3)
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    
    dia = agora.day
    mes = agora.month
    ano = agora.year

    # Salva no arquivo CSV local com a coluna "Quem" no final
    with open(ARQUIVO_CSV, mode="a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow([descricao, f"{valor:.2f}", mes, dia, ano, categoria, descricao, quem])

    await update.message.reply_text(
        text=(
            f"✅ **Gasto salvo com sucesso!**\n\n"
            f"👤 Quem: {quem}\n"
            f"📅 Data: {dia:02d}/{mes:02d}/{ano}\n"
            f"💵 Valor: R$ {valor:.2f}\n"
            f"🏷️ Categoria: {categoria}\n"
            f"💬 Descrição: {descricao}"
        ),
        parse_mode="Markdown",
    )

    # Envia automaticamente o arquivo CSV atualizado como backup no chat
    with open(ARQUIVO_CSV, "rb") as arquivo:
        await update.message.reply_document(
            document=arquivo,
            filename="gastos.csv",
            caption="📊 Planilha atualizada com este novo lançamento!"
        )

    return ConversationHandler.END


async def resumo_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calcula e envia um resumo dos gastos direto no chat."""
    if not os.path.exists(ARQUIVO_CSV) or os.path.getsize(ARQUIVO_CSV) == 0:
        await update.message.reply_text("📭 Ainda não há gastos registrados para resumir.")
        return

    total_geral = 0.0
    por_categoria = {}
    por_pessoa = {"Fernando": 0.0, "Namorada": 0.0}

    with open(ARQUIVO_CSV, mode="r", encoding="utf-8") as arquivo:
        leitor = csv.reader(arquivo)
        cabecalho = next(leitor, None)  # Pula o cabeçalho

        for linha in leitor:
            if len(linha) >= 8:
                try:
                    valor = float(linha[1])
                    categoria = linha[5]
                    quem = linha[7]

                    total_geral += valor
                    por_categoria[categoria] = por_categoria.get(categoria, 0.0) + valor
                    if quem in por_pessoa:
                        por_pessoa[quem] += valor
                    else:
                        por_pessoa[quem] = por_pessoa.get(quem, 0.0) + valor
                except ValueError:
                    continue

    texto_resumo = f"📈 **Resumo de Gastos**\n\n"
    texto_resumo += f"💵 **Total Geral:** R$ {total_geral:.2f}\n\n"
    
    texto_resumo += "👤 **Por Pessoa:**\n"
    for pessoa, val in por_pessoa.items():
        texto_resumo += f"• {pessoa}: R$ {val:.2f}\n"

    texto_resumo += "\n🏷️ **Por Categoria:**\n"
    for cat, val in por_categoria.items():
        texto_resumo += f"• {cat}: R$ {val:.2f}\n"

    await update.message.reply_text(texto_resumo, parse_mode="Markdown")


async def exportar_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o arquivo CSV de backup a qualquer momento com /exportar."""
    if not os.path.exists(ARQUIVO_CSV) or os.path.getsize(ARQUIVO_CSV) == 0:
        await update.message.reply_text("📭 Ainda não há gastos registrados para exportar.")
        return

    with open(ARQUIVO_CSV, "rb") as arquivo:
        await update.message.reply_document(
            document=arquivo,
            filename="gastos.csv",
            caption="📊 Aqui está o seu backup atualizado dos gastos!"
        )


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registro cancelado.")
    return ConversationHandler.END


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", iniciar_gasto)],
        states={
            QUEM: [CallbackQueryHandler(receber_quem)],
            VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_valor)],
            CATEGORIA: [CallbackQueryHandler(receber_categoria)],
            DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_descricao)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("resumo", resumo_gastos))
    app.add_handler(CommandHandler("exportar", exportar_csv))

    print(f"Iniciando bot via Webhook na porta {PORT}...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{RENDER_URL}/{TOKEN}",
    )


if __name__ == "__main__":
    main()
